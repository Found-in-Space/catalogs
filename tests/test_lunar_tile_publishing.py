"""Protect immutable publication, resumption, and descriptor promotion."""

import base64
import hashlib
import io
import runpy
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

TOOL = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/publish_lunar_tiles.py")
)


class Store:
    def __init__(self):
        self.objects = {}
        self.puts = []

    def head_object(self, *, Bucket, Key, ChecksumMode):
        assert ChecksumMode == "ENABLED"
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return self.objects[Key]

    def put_object(
        self,
        *,
        Bucket,
        Key,
        Body,
        ContentLength,
        ContentType,
        CacheControl,
        ChecksumSHA256,
        IfNoneMatch,
    ):
        assert IfNoneMatch == "*"
        if Key in self.objects:
            raise ClientError({"Error": {"Code": "412"}}, "PutObject")
        content = Body.read()
        assert len(content) == ContentLength
        assert (
            base64.b64encode(hashlib.sha256(content).digest()).decode()
            == ChecksumSHA256
        )
        self.puts.append(Key)
        self.objects[Key] = {
            "ContentLength": ContentLength,
            "ContentType": ContentType,
            "CacheControl": CacheControl,
            "ChecksumSHA256": ChecksumSHA256,
        }

    def get_paginator(self, operation):
        assert operation == "list_objects_v2"
        return self

    def paginate(self, *, Bucket, Prefix):
        yield {
            "Contents": [
                {"Key": key, "Size": value["ContentLength"]}
                for key, value in self.objects.items()
                if key.startswith(Prefix)
            ]
        }


def row(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {
        "path": name,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "content_type": "application/json" if name.endswith(".json") else "image/png",
    }


def test_upload_resume_and_reject_remote_corruption(tmp_path):
    item = row(tmp_path, "imagery/0/0/0.png", b"tile")
    store = Store()
    assert (
        TOOL["publish_object"](store, tmp_path, "bucket", "release/", item)
        == "uploaded"
    )
    assert (
        TOOL["publish_object"](store, tmp_path, "bucket", "release/", item)
        == "existing"
    )
    assert store.puts == ["release/imagery/0/0/0.png"]
    store.objects[store.puts[0]]["ChecksumSHA256"] = "wrong"
    with pytest.raises(ValueError, match="checksum conflict"):
        TOOL["publish_object"](store, tmp_path, "bucket", "release/", item)
    assert len(store.puts) == 1


def test_local_corruption_cannot_be_published(tmp_path):
    item = row(tmp_path, "imagery/0/0/0.png", b"tile")
    (tmp_path / item["path"]).write_bytes(b"fake")
    store = Store()
    with pytest.raises(ValueError, match="Local checksum changed"):
        TOOL["publish_object"](store, tmp_path, "bucket", "release/", item)
    assert not store.puts


def test_descriptor_promoted_last_and_inventory_must_match(tmp_path):
    items = [
        row(tmp_path, "imagery/0/0/0.png", b"tile"),
        row(tmp_path, "product.json", b"{}"),
    ]
    store = Store()
    assert TOOL["publish"](store, tmp_path, "bucket", "release/", items, 2) == {
        "uploaded": 2,
        "existing": 0,
    }
    assert store.puts[-1] == "release/product.json"
    store.objects["release/unexpected"] = {"ContentLength": 4}
    with pytest.raises(ValueError, match="Unexpected remote object"):
        TOOL["verify_inventory"](store, "bucket", "release/", items)


def test_failed_tiles_cannot_promote_descriptor(tmp_path):
    items = [
        row(tmp_path, "imagery/0/0/0.png", b"tile"),
        row(tmp_path, "product.json", b"{}"),
    ]
    (tmp_path / items[0]["path"]).write_bytes(b"fake")
    store = Store()
    with pytest.raises(ValueError, match="Local checksum changed"):
        TOOL["publish"](store, tmp_path, "bucket", "release/", items, 2)
    assert "release/product.json" not in store.puts


def test_one_bandwidth_budget_is_shared_between_streams_and_retries():
    elapsed = [0.0]
    sleeps = []

    def sleep(delay):
        sleeps.append(delay)
        elapsed[0] += delay

    limiter = TOOL["BandwidthLimiter"](1024, clock=lambda: elapsed[0], sleep=sleep)
    first = TOOL["RateLimitedReader"](io.BytesIO(b"a" * 1024), limiter)
    second = TOOL["RateLimitedReader"](io.BytesIO(b"b" * 1024), limiter)
    assert first.read(512) == b"a" * 512
    assert second.read() == b"b" * 1024
    first.seek(0)
    assert first.read() == b"a" * 1024
    assert first.tell() == 1024
    assert first.read() == b""
    assert elapsed[0] == 2.5
    assert sum(sleeps) == 2.5
