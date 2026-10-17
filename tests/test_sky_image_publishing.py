import base64
import hashlib
import json
import runpy
from email.message import Message
from io import BytesIO
from pathlib import Path

import pytest

API = runpy.run_path(str(Path(__file__).parents[1] / "scripts/publish_sky_image.py"))


def test_payload_tampering_fails_before_upload(tmp_path):
    for name in API["TYPES"]:
        (tmp_path / name).write_bytes(b"image" if name.endswith("webp") else b"text")
    image = "deep-star-map-2020-4k.webp"
    (tmp_path / "product.json").write_text(json.dumps({"release": "20261017.1",
        "productId": "deep-star-maps-2020-celestial-4k", "output": {"path": image,
        "sha256": hashlib.sha256(b"image").hexdigest(), "bytes": 5}}))
    names = set(API["TYPES"]) - {"checksums.sha256"}
    (tmp_path / "checksums.sha256").write_text("".join(
        f"{hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()}  {name}\n" for name in sorted(names)))
    assert API["plan"](tmp_path)[-1]["path"] == "product.json"
    (tmp_path / image).write_bytes(b"other")
    with pytest.raises(ValueError, match="checksum differs"):
        API["plan"](tmp_path)


def test_existing_object_must_match_sha256_and_delivery_metadata():
    checksum = hashlib.sha256(b"image").hexdigest()
    row = {"path": "sky.webp", "sha256": checksum, "bytes": 5, "content_type": "image/webp"}
    head = {"ChecksumSHA256": base64.b64encode(bytes.fromhex(checksum)).decode(),
            "ContentLength": 5, "ContentType": "image/webp", "CacheControl": API["CACHE"]}
    API["check_head"](head, row)
    for field in head:
        invalid = {**head, field: "changed"}
        with pytest.raises(ValueError, match="conflict"):
            API["check_head"](invalid, row)


def test_upload_uses_conditional_create_and_publishes_descriptor_last(tmp_path, monkeypatch):
    rows = []
    stored = {}
    written = []
    for name in ["sky.webp", "product.json"]:
        (tmp_path / name).write_bytes(name.encode())
        rows.append({"path": name, "sha256": hashlib.sha256(name.encode()).hexdigest(),
                     "bytes": len(name), "content_type": "image/webp" if name.endswith("webp") else "application/json"})

    def fake_aws(profile, action, *arguments, **kwargs):
        if action == "list-objects-v2":
            return {"Contents": [{"Key": key, "Size": head["ContentLength"]} for key, head in stored.items()]}
        key = arguments[arguments.index("--key") + 1]
        if action == "head-object":
            return stored.get(key)
        assert action == "put-object"
        assert arguments[arguments.index("--if-none-match") + 1] == "*"
        assert key not in stored
        written.append(key)
        row = next(row for row in rows if key.endswith(row["path"]))
        stored[key] = {"ChecksumSHA256": base64.b64encode(bytes.fromhex(row["sha256"])).decode(),
                       "ContentLength": row["bytes"], "ContentType": row["content_type"], "CacheControl": API["CACHE"]}
        return {}

    def fake_urlopen(request, **kwargs):
        row = next(row for row in rows if request.full_url.endswith(row["path"]))
        response = BytesIO(row["path"].encode())
        response.status = 200
        response.headers = Message()
        for key, value in {"Access-Control-Allow-Origin": "*", "Cache-Control": API["CACHE"],
                           "Content-Type": row["content_type"]}.items():
            response.headers[key] = value
        return response

    monkeypatch.setitem(API["publish"].__globals__, "aws", fake_aws)
    monkeypatch.setitem(API["publish"].__globals__, "urlopen", fake_urlopen)
    receipt = API["publish"](tmp_path, rows, None)
    assert len(receipt["objects"]) == 2
    assert written[-1].endswith("product.json")
    # Restarting verifies existing objects without overwriting them.
    API["publish"](tmp_path, rows, None)
    assert len(written) == 2
