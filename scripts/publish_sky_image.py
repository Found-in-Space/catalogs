"""Check or publish the authenticated sky-image payload. Dry run by default.

Uses the installed AWS CLI, including its existing authentication. New objects
use conditional writes; existing objects must match bytes and delivery metadata.
The receipt is produced only after complete S3 and public CDN verification.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

BUCKET = "foundinspace"
PREFIX = "textures/sky/deep-star-maps-2020/20261017.1/"
BASE = "https://data.foundin.space/" + PREFIX
CACHE = "public, max-age=31536000, immutable"
TYPES = {"deep-star-map-2020-4k.webp": "image/webp", "product.json": "application/json",
         "NOTICE.md": "text/markdown; charset=utf-8", "LICENSE.txt": "text/plain; charset=utf-8",
         "checksums.sha256": "text/plain; charset=utf-8"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def plan(root):
    require({p.name for p in root.iterdir()} == set(TYPES), "Unexpected payload files")
    for name in TYPES:
        require((root / name).is_file() and not (root / name).is_symlink(), "Nonregular payload file")
    recorded = {}
    for line in (root / "checksums.sha256").read_text().splitlines():
        checksum, name = line.split("  ", 1)
        require(name in TYPES and name not in recorded, "Invalid or duplicate checksum entry")
        require(checksum == digest(root / name), "Payload checksum differs: " + name)
        recorded[name] = checksum
    require(set(recorded) == set(TYPES) - {"checksums.sha256"}, "Incomplete payload checksums")
    product = json.loads((root / "product.json").read_text())
    require(product["release"] == "20261017.1" and
            product["productId"] == "deep-star-maps-2020-celestial-4k", "Unexpected product")
    image = product["output"]
    require(image["path"] == "deep-star-map-2020-4k.webp", "Unexpected image path")
    require(image["sha256"] == recorded[image["path"]] and
            image["bytes"] == (root / image["path"]).stat().st_size, "Product image identity differs")
    # Publish the descriptor last, after every referenced object is verified.
    return [{"path": name, "sha256": digest(root / name), "bytes": (root / name).stat().st_size,
             "content_type": TYPES[name]} for name in [*sorted(set(TYPES) - {"product.json"}), "product.json"]]


def check_head(head, row):
    expected = base64.b64encode(bytes.fromhex(row["sha256"])).decode()
    require(head.get("ChecksumSHA256") == expected, "Remote checksum conflict: " + row["path"])
    require(head.get("ContentLength") == row["bytes"], "Remote size conflict: " + row["path"])
    require(head.get("ContentType") == row["content_type"], "Remote content type conflict: " + row["path"])
    require(head.get("CacheControl") == CACHE, "Remote cache conflict: " + row["path"])


def aws(profile, *args, missing_ok=False):
    command = ["aws", "--region", "eu-central-1", "--output", "json"]
    if profile:
        command += ["--profile", profile]
    result = subprocess.run([*command, "s3api", *args], capture_output=True, text=True)
    if missing_ok and result.returncode and "(404)" in result.stderr:
        return None
    require(result.returncode == 0, result.stderr.strip())
    return json.loads(result.stdout or "{}")


def publish(root, rows, profile):
    for row in rows:
        key = PREFIX + row["path"]
        arguments = ["--bucket", BUCKET, "--key", key]
        head = aws(profile, "head-object", *arguments, "--checksum-mode", "ENABLED", missing_ok=True)
        if head is None:
            # Do not overwrite a concurrent publisher, even between HEAD and PUT.
            aws(profile, "put-object", *arguments, "--body", str(root / row["path"]),
                "--content-type", row["content_type"], "--cache-control", CACHE,
                "--checksum-algorithm", "SHA256", "--checksum-sha256",
                base64.b64encode(bytes.fromhex(row["sha256"])).decode(), "--if-none-match", "*")
            head = aws(profile, "head-object", *arguments, "--checksum-mode", "ENABLED")
        check_head(head, row)
    remote = aws(profile, "list-objects-v2", "--bucket", BUCKET, "--prefix", PREFIX)
    require({item["Key"]: item["Size"] for item in remote.get("Contents", [])} ==
            {PREFIX + row["path"]: row["bytes"] for row in rows}, "Remote inventory differs")
    verified = []
    for row in rows:
        request = Request(BASE + row["path"], headers={"Origin": "https://foundin.space"})
        with urlopen(request, timeout=45) as response:
            payload = response.read()
            require(response.status == 200 and len(payload) == row["bytes"], "CDN response size differs")
            require(hashlib.sha256(payload).hexdigest() == row["sha256"], "CDN checksum differs")
            headers = response.headers
            require(headers.get("Access-Control-Allow-Origin") in {"*", "https://foundin.space"}, "CDN CORS missing")
            require(headers.get("Cache-Control") == CACHE, "CDN cache differs")
            require(headers.get("Content-Type") == row["content_type"], "CDN content type differs")
            verified.append({**row, "url": request.full_url, "status": response.status,
                             "cors": headers["Access-Control-Allow-Origin"], "cache_control": headers["Cache-Control"]})
    return {"verified_at": datetime.now(UTC).isoformat(), "bucket": BUCKET, "prefix": PREFIX,
            "base_url": BASE, "objects": verified}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--profile")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    rows = plan(args.payload)
    if not args.publish:
        print(json.dumps({"bucket": BUCKET, "prefix": PREFIX, "objects": rows}, indent=2))
        return
    require(args.receipt is not None, "Publishing requires a receipt destination")
    receipt = publish(args.payload, rows, args.profile)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"verified_objects": len(rows), "base_url": BASE}))


if __name__ == "__main__":
    main()
