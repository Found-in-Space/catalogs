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
CAP_TYPES = {f"deep-star-map-2020-{pole}-1024.webp": "image/webp" for pole in ["north", "south"]}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def plan(root):
    product = json.loads((root / "product.json").read_text())
    require(product["release"] in {"20261017.1", "20261017.2"} and
            product["productId"] == "deep-star-maps-2020-celestial-4k", "Unexpected product")
    types = {**TYPES, **(CAP_TYPES if product["release"] == "20261017.2" else {})}
    require({p.name for p in root.iterdir()} == set(types), "Unexpected payload files")
    for name in types:
        require((root / name).is_file() and not (root / name).is_symlink(), "Nonregular payload file")
    recorded = {}
    for line in (root / "checksums.sha256").read_text().splitlines():
        checksum, name = line.split("  ", 1)
        require(name in types and name not in recorded, "Invalid or duplicate checksum entry")
        require(checksum == digest(root / name), "Payload checksum differs: " + name)
        recorded[name] = checksum
    require(set(recorded) == set(types) - {"checksums.sha256"}, "Incomplete payload checksums")
    image = product["output"]
    require(image["path"] == "deep-star-map-2020-4k.webp", "Unexpected image path")
    require(image["sha256"] == recorded[image["path"]] and
            image["bytes"] == (root / image["path"]).stat().st_size, "Product image identity differs")
    if product["release"] == "20261017.2":
        caps = product["polarCaps"]
        require(caps["projection"] == "gnomonic" and caps["halfAngleDegrees"] == 35 and
                caps["rightAxis"] == "+X" and caps["topAxis"] == "+Y" and
                caps["northAxis"] == "+Z" and caps["southAxis"] == "-Z", "Unexpected polar projection")
        for pole in ["north", "south"]:
            cap = caps[pole]
            require(cap["path"] == f"deep-star-map-2020-{pole}-1024.webp" and
                    cap["width"] == cap["height"] == 1024, "Unexpected cap image")
            require(cap["sha256"] == recorded[cap["path"]] and
                    cap["bytes"] == (root / cap["path"]).stat().st_size, "Cap identity differs")
    # Publish the descriptor last, after every referenced object is verified.
    return [{"path": name, "sha256": digest(root / name), "bytes": (root / name).stat().st_size,
             "content_type": types[name]} for name in [*sorted(set(types) - {"product.json"}), "product.json"]]


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


def publish(root, rows, profile, prefix=PREFIX):
    base = "https://data.foundin.space/" + prefix
    for row in rows:
        key = prefix + row["path"]
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
    remote = aws(profile, "list-objects-v2", "--bucket", BUCKET, "--prefix", prefix)
    require({item["Key"]: item["Size"] for item in remote.get("Contents", [])} ==
            {prefix + row["path"]: row["bytes"] for row in rows}, "Remote inventory differs")
    verified = []
    for row in rows:
        request = Request(base + row["path"], headers={"Origin": "https://foundin.space"})
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
    return {"verified_at": datetime.now(UTC).isoformat(), "bucket": BUCKET, "prefix": prefix,
            "base_url": base, "objects": verified}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--profile")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    rows = plan(args.payload)
    release = json.loads((args.payload / "product.json").read_text())["release"]
    prefix = f"textures/sky/deep-star-maps-2020/{release}/"
    if not args.publish:
        print(json.dumps({"bucket": BUCKET, "prefix": prefix, "objects": rows}, indent=2))
        return
    require(args.receipt is not None, "Publishing requires a receipt destination")
    receipt = publish(args.payload, rows, args.profile, prefix)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"verified_objects": len(rows), "base_url": receipt["base_url"]}))


if __name__ == "__main__":
    main()
