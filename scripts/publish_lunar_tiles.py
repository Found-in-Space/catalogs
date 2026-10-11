"""Publish an authenticated texture tree to an immutable S3 prefix.

Use the locked publication dependency group. A dry run is the default.
Existing objects must have matching S3 SHA-256 checksums and delivery metadata.
The descriptor is published last; a receipt is written only after verification.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

CACHE_CONTROL = "public, max-age=31536000, immutable"
TILE_PATH = re.compile(r"imagery/(\d+)/(\d+)/(\d+)\.png\Z")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def plan(output: Path) -> tuple[dict, list[dict]]:
    product = json.loads((output / "product.json").read_text())
    objects = []
    manifests = []
    manifest_set = []
    for level in product["levels"]:
        zoom = level["zoom"]
        name = level["manifest"]
        require(name == f"manifests/tiles-z{zoom}.sha256", "Unexpected manifest path")
        manifest = output / name
        require(digest(manifest) == level["manifest_sha256"], "Manifest changed")
        manifest_set.append({"zoom": zoom, "manifest_sha256": digest(manifest)})
        seen = set()
        total_bytes = 0
        for line in manifest.read_text(encoding="ascii").splitlines():
            checksum, separator, relative = line.partition("  ")
            match = TILE_PATH.fullmatch(relative)
            require(
                bool(separator and re.fullmatch(r"[0-9a-f]{64}", checksum) and match),
                "Invalid tile entry",
            )
            z, x, y = map(int, match.groups())
            require(z == zoom and x < 2**z and y < 2**z, "Tile outside level")
            require(relative not in seen, "Duplicate tile")
            seen.add(relative)
            path = output / relative
            require(
                path.is_file() and not path.is_symlink(), "Missing or symlinked tile"
            )
            size = path.stat().st_size
            total_bytes += size
            objects.append(
                {
                    "path": relative,
                    "sha256": checksum,
                    "bytes": size,
                    "content_type": "image/png",
                }
            )
        require(len(seen) == level["tile_count"] == 4**zoom, "Incomplete level")
        require(total_bytes == level["tile_bytes"], "Level size differs")
        manifests.append(
            {
                "path": name,
                "sha256": digest(manifest),
                "bytes": manifest.stat().st_size,
                "content_type": "text/plain; charset=utf-8",
            }
        )
    canonical = json.dumps(
        manifest_set, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    require(
        hashlib.sha256(canonical).hexdigest() == product["manifest_set_sha256"],
        "Manifest set changed",
    )
    require(len(objects) == product["tiles"]["total_count"], "Total count differs")
    require(
        sum(row["bytes"] for row in objects) == product["tiles"]["total_bytes"],
        "Total size differs",
    )
    require(
        sum(path.is_file() for path in (output / "imagery").rglob("*")) == len(objects),
        "Unlisted imagery file",
    )
    objects.extend(manifests)
    descriptor = output / "product.json"
    objects.append(
        {
            "path": "product.json",
            "sha256": digest(descriptor),
            "bytes": descriptor.stat().st_size,
            "content_type": "application/json",
        }
    )
    return product, objects


def checksum64(row: dict) -> str:
    return base64.b64encode(bytes.fromhex(row["sha256"])).decode("ascii")


def check_head(head: dict, row: dict) -> None:
    require(
        head.get("ChecksumSHA256") == checksum64(row),
        f"Remote checksum conflict: {row['path']}",
    )
    require(
        head["ContentLength"] == row["bytes"], f"Remote size conflict: {row['path']}"
    )
    require(
        head.get("ContentType") == row["content_type"],
        f"Remote content type conflict: {row['path']}",
    )
    require(
        head.get("CacheControl") == CACHE_CONTROL,
        f"Remote cache policy conflict: {row['path']}",
    )


def publish_object(client, output: Path, bucket: str, prefix: str, row: dict) -> str:
    path = output / row["path"]
    require(digest(path) == row["sha256"], f"Local checksum changed: {row['path']}")
    key = prefix + row["path"]
    try:
        head = client.head_object(Bucket=bucket, Key=key, ChecksumMode="ENABLED")
    except ClientError as error:
        if error.response["Error"]["Code"] not in {"404", "NoSuchKey", "NotFound"}:
            raise
    else:
        check_head(head, row)
        return "existing"
    with path.open("rb") as stream:
        try:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=stream,
                ContentLength=row["bytes"],
                ContentType=row["content_type"],
                CacheControl=CACHE_CONTROL,
                ChecksumSHA256=checksum64(row),
                IfNoneMatch="*",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] not in {"412", "PreconditionFailed"}:
                raise
    check_head(client.head_object(Bucket=bucket, Key=key, ChecksumMode="ENABLED"), row)
    return "uploaded"


def verify_inventory(
    client,
    bucket: str,
    prefix: str,
    objects: list[dict],
    *,
    allow_missing_descriptor: bool = False,
) -> None:
    expected = {prefix + row["path"]: row["bytes"] for row in objects}
    for page in client.get_paginator("list_objects_v2").paginate(
        Bucket=bucket, Prefix=prefix
    ):
        for row in page.get("Contents", []):
            require(
                expected.pop(row["Key"], None) == row["Size"],
                "Unexpected remote object or size",
            )
    if allow_missing_descriptor:
        expected.pop(prefix + "product.json", None)
    require(not expected, "Missing remote objects")


def verify_cdn(base: str, objects: list[dict]) -> list[dict]:
    samples = {
        "product.json",
        "imagery/0/0/0.png",
        "imagery/4/8/8.png",
        "imagery/8/0/0.png",
        "imagery/8/255/255.png",
        "imagery/8/128/128.png",
        "imagery/8/127/42.png",
    }
    results = []
    for row in objects:
        if row["path"] not in samples:
            continue
        url = base + row["path"]
        request = Request(url, headers={"Origin": "https://foundin.space"})
        with urlopen(request, timeout=60) as response:
            payload = response.read()
            require(response.status == 200, "CDN did not return a complete object")
            require(
                hashlib.sha256(payload).hexdigest() == row["sha256"],
                "CDN checksum differs",
            )
            require(len(payload) == row["bytes"], "CDN size differs")
            require(
                response.headers.get("Access-Control-Allow-Origin")
                in {"*", "https://foundin.space"},
                "CDN CORS missing",
            )
            require(
                response.headers.get("Cache-Control") == CACHE_CONTROL,
                "CDN cache policy differs",
            )
            require(
                response.headers.get("Content-Type") == row["content_type"],
                "CDN content type differs",
            )
            results.append(
                {
                    "path": row["path"],
                    "url": url,
                    "sha256": row["sha256"],
                    "bytes": len(payload),
                    "status": response.status,
                    "cors": response.headers["Access-Control-Allow-Origin"],
                    "cache_control": response.headers["Cache-Control"],
                    "content_type": response.headers["Content-Type"],
                }
            )
    return results


def publish(
    client, output: Path, bucket: str, prefix: str, objects: list[dict], workers: int
) -> dict:
    counts = {"uploaded": 0, "existing": 0}
    # Keep queued work bounded; process the descriptor after every other object.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = deque()

        def finish_one():
            counts[pending.popleft().result()] += 1
            completed = sum(counts.values())
            if completed % 1000 == 0:
                print(
                    f"Verified {completed:,}/{len(objects):,} objects",
                    file=sys.stderr,
                    flush=True,
                )

        for row in objects[:-1]:
            pending.append(
                pool.submit(publish_object, client, output, bucket, prefix, row)
            )
            if len(pending) >= workers * 2:
                finish_one()
        while pending:
            finish_one()
    verify_inventory(client, bucket, prefix, objects, allow_missing_descriptor=True)
    counts[publish_object(client, output, bucket, prefix, objects[-1])] += 1
    verify_inventory(client, bucket, prefix, objects)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--profile")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    require(bool(re.fullmatch(r"\d{8}\.[1-9]\d*", args.release)), "Invalid release")
    require(args.workers > 0, "Workers must be positive")
    output = args.output_root.resolve()
    product, objects = plan(output)
    require(
        product["product_id"] == "moon-lroc-wac-global-morphology-100m-v1",
        "Unexpected lunar product",
    )
    bucket = "foundinspace"
    prefix = f"textures/moon/lroc-wac-global-100m/{args.release}/"
    cdn = f"https://data.foundin.space/{prefix}"
    summary = {
        "product_identity_sha256": product["product_identity_sha256"],
        "product_json_sha256": objects[-1]["sha256"],
        "manifest_set_sha256": product["manifest_set_sha256"],
        "bucket": bucket,
        "prefix": prefix,
        "cdn_base_url": cdn,
        "object_count": len(objects),
        "total_bytes": sum(row["bytes"] for row in objects),
    }
    print(json.dumps(summary, indent=2), flush=True)
    if not args.publish:
        return
    repository = Path(__file__).resolve().parents[1]

    def git(*arguments):
        return subprocess.check_output(
            ["git", "-C", str(repository), *arguments], text=True
        ).strip()

    require(
        not git("status", "--porcelain", "--untracked-files=all"),
        "Publishing requires a clean checkout",
    )
    commit = git("rev-parse", "HEAD")
    require(
        bool(git("branch", "-r", "--contains", commit)),
        "Push publisher code before creating release evidence",
    )
    require(
        args.receipt is not None and not args.receipt.exists(),
        "A new receipt path is required",
    )
    require(
        not args.receipt.resolve().is_relative_to(output),
        "Keep receipt outside payload",
    )
    session = boto3.Session(profile_name=args.profile, region_name="eu-central-1")
    client = session.client(
        "s3",
        config=Config(
            max_pool_connections=args.workers,
            retries={"mode": "adaptive", "max_attempts": 10},
        ),
    )
    started = datetime.now(UTC).isoformat()
    counts = publish(client, output, bucket, prefix, objects, args.workers)
    cdn_checks = verify_cdn(cdn, objects)
    receipt = {
        "format_version": 1,
        **summary,
        "started_at": started,
        "completed_at": datetime.now(UTC).isoformat(),
        "all_remote_sha256_sizes_and_metadata_verified": True,
        "exact_remote_inventory_verified": True,
        "descriptor_published_last": True,
        "immutable_conditional_writes": True,
        "counts": counts,
        "workers": args.workers,
        "cdn_checks": cdn_checks,
        "boto3_version": boto3.__version__,
    }
    receipt.update(
        {
            "publisher_repository": "https://github.com/Found-in-Space/catalogs",
            "publisher_commit": commit,
            "python_version": sys.version.split()[0],
        }
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.receipt.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    temporary.replace(args.receipt)
    print(
        f"Published and verified {len(objects):,} objects; receipt: {args.receipt}",
        flush=True,
    )


if __name__ == "__main__":
    main()
