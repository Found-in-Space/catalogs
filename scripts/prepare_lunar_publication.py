"""Prepare an authenticated lunar-texture candidate without importing its producer.

Run this committed script from a clean checkout of its public catalogs commit.
The producer's recorded reports remain evidence, not proof of publication readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import UTC, datetime
from pathlib import Path

SERIES = "fis.textures.moon.lroc-wac-global-morphology-100m"
TITLE = "Found in Space lunar display textures: LROC WAC global morphology 100 m"
PRODUCER_URL = "https://github.com/Found-in-Space/pas-de-geant-texture-pipeline"
SOURCE_PAGE = "https://astrogeology.usgs.gov/search/map/moon_lro_lroc_wac_global_morphology_mosaic_100m"
PROJECT_PATH = "projects/moon/lroc-wac-global-100m/project.toml"
SOURCE_PATH = (
    "projects/moon/lroc-wac-global-100m/sources/lroc-wac-global-morphology-100m.toml"
)
CRS_PATHS = (
    "resources/crs/moon-geographic-1737400.wkt",
    "resources/crs/moon-simple-cylindrical-1737400.wkt",
)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
TILE_PATH = re.compile(r"imagery/(\d+)/(\d+)/(\d+)\.png\Z")


def git(repository: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repository), *args], text=True
    ).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def portable(value, run_root: Path, producer_root: Path):
    """Preserve run-relative roles, command arguments, and public URLs."""
    if isinstance(value, dict):
        return {
            key: portable(item, run_root, producer_root) for key, item in value.items()
        }
    if isinstance(value, list):
        return [portable(item, run_root, producer_root) for item in value]
    if isinstance(value, str):
        for root, token in (
            (producer_root, "${PRODUCER_ROOT}"),
            (run_root, "${RUN_ROOT}"),
        ):
            value = value.replace(str(root), token)
        require(not value.startswith("/"), f"Unmapped absolute path: {value}")
        require(
            not re.search(r"/(?:data|home|tmp|Users)/", value), "Embedded local path"
        )
        if "://" in value:
            from urllib.parse import urlsplit

            url = urlsplit(value)
            require(
                url.scheme == "https" and not url.username and not url.password,
                "Unexpected URL scheme or embedded credentials",
            )
            require(
                not url.query and not url.fragment, "URL requires public-source review"
            )
            require(
                url.hostname
                in {
                    "astrogeology.usgs.gov",
                    "planetarymaps.usgs.gov",
                    "asc-pds-services.s3.us-west-2.amazonaws.com",
                },
                "Unreviewed evidence URL",
            )
    return value


def producer_identities(value):
    if isinstance(value, dict):
        if "producer" in value and isinstance(value["producer"], dict):
            yield value["producer"]
        for item in value.values():
            yield from producer_identities(item)
    elif isinstance(value, list):
        for item in value:
            yield from producer_identities(item)


def verify_tiles(output: Path, product: dict, validation: dict) -> list[dict]:
    require(validation.get("valid") is True, "Producer validation did not pass")
    require(
        all(item is True for item in validation["checks"].values()),
        "Incomplete tile checks",
    )
    require(
        validation["product_json_sha256"] == sha256(output / "product.json"),
        "Product JSON differs from validated product",
    )
    require(
        validation["product_identity_sha256"] == product["product_identity_sha256"],
        "Product identity differs from validation",
    )
    rows = []
    manifest_set = []
    for level in product["levels"]:
        zoom = level["zoom"]
        manifest = output / level["manifest"]
        require(
            level["manifest"] == f"manifests/tiles-z{zoom}.sha256",
            "Unexpected manifest path",
        )
        digest = sha256(manifest)
        require(digest == level["manifest_sha256"], "Tile manifest changed")
        manifest_set.append({"zoom": zoom, "manifest_sha256": digest})
        count = total_bytes = 0
        seen = set()
        with manifest.open(encoding="ascii") as stream:
            for line in stream:
                checksum, separator, name = line.rstrip("\n").partition("  ")
                match = TILE_PATH.fullmatch(name)
                require(
                    bool(separator and SHA256.fullmatch(checksum) and match),
                    "Invalid tile manifest entry",
                )
                z, x, y = map(int, match.groups())
                require(
                    z == zoom and x < 2**z and y < 2**z, "Tile address outside level"
                )
                require((x, y) not in seen, "Duplicate tile address")
                seen.add((x, y))
                tile = output / name
                require(
                    tile.is_file() and not tile.is_symlink(),
                    "Missing or symlinked tile",
                )
                require(sha256(tile) == checksum, f"Tile checksum mismatch: {name}")
                count += 1
                total_bytes += tile.stat().st_size
        require(count == level["tile_count"] == 4**zoom, "Tile count mismatch")
        require(total_bytes == level["tile_bytes"], "Tile byte count mismatch")
        rows.append(
            {
                "zoom": zoom,
                "count": count,
                "bytes": total_bytes,
                "manifest": level["manifest"],
                "sha256": digest,
            }
        )
    manifest_digest = hashlib.sha256(
        json.dumps(
            manifest_set, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()
    require(
        manifest_digest == product["manifest_set_sha256"],
        "Manifest-set identity mismatch",
    )
    require(
        [row["zoom"] for row in rows]
        == list(
            range(
                product["tiles"]["minimum_zoom"], product["tiles"]["maximum_zoom"] + 1
            )
        ),
        "Non-contiguous or unordered pyramid",
    )
    require(
        sum(row["count"] for row in rows)
        == product["tiles"]["total_count"]
        == validation["tile_count"],
        "Total tile count mismatch",
    )
    require(
        sum(row["bytes"] for row in rows)
        == product["tiles"]["total_bytes"]
        == validation["tile_bytes"],
        "Total tile size mismatch",
    )
    actual = sum(1 for path in (output / "imagery").rglob("*") if path.is_file())
    require(actual == product["tiles"]["total_count"], "Unexpected imagery files")
    return rows


def code_tree_sha256(repository: Path, commit: str) -> str:
    paths = git(repository, "ls-tree", "-r", "--name-only", commit).splitlines()
    digest = hashlib.sha256()
    for name in sorted(
        name
        for name in paths
        if (name.startswith("src/") and name.endswith(".py"))
        or name in ("pyproject.toml", "uv.lock")
    ):
        content = subprocess.check_output(
            ["git", "-C", str(repository), "show", f"{commit}:{name}"]
        )
        digest.update(
            name.encode() + b"\0" + hashlib.sha256(content).hexdigest().encode() + b"\n"
        )
    return digest.hexdigest()


def regenerate_checksums(release: Path) -> None:
    lines = []
    for path in sorted(release.rglob("*")):
        name = path.relative_to(release).as_posix()
        if path.is_file() and name not in (
            "checksums.sha256",
            "zenodo/published-record.toml",
        ):
            lines.append(f"{sha256(path)}  {name}\n")
    (release / "checksums.sha256").write_text("".join(lines), encoding="ascii")


def prepare(
    *, run_root: Path, producer_root: Path, release: str, destination: Path
) -> dict:
    repository = Path(__file__).resolve().parents[1]
    require(re.fullmatch(r"\d{8}\.[1-9]\d*", release) is not None, "Invalid release ID")
    require(
        not destination.exists(), "Destination already exists; never replace a release"
    )
    require(
        not git(repository, "status", "--porcelain", "--untracked-files=all"),
        "Assembly requires a clean committed catalogs checkout",
    )
    assembly_commit = git(repository, "rev-parse", "HEAD")
    require(
        git(repository, "remote", "-v").find("github.com") >= 0,
        "No public catalogs remote",
    )
    require(
        bool(git(repository, "branch", "-r", "--contains", assembly_commit)),
        "Assembly commit must be pushed before preparing publication artifacts",
    )
    require(
        not git(producer_root, "status", "--porcelain", "--untracked-files=all"),
        "Producer checkout must be clean; inputs are read from recorded Git objects",
    )
    output = run_root / "output"
    product = read_json(output / "product.json")
    validation = read_json(run_root / "evidence/tiles.validation.json")
    require(
        product["product_id"] == "moon-lroc-wac-global-morphology-100m-v1",
        "Unexpected product",
    )
    require(
        product["tiles"]["addressing"] == "XYZ" and product["tiles"]["opaque"] is True,
        "Unexpected texture contract",
    )
    require(
        product["tiles"]["tile_size"] == 512
        and product["tiles"]["minimum_zoom"] == 0
        and product["tiles"]["maximum_zoom"] == 8
        and product["tiles"]["channels"] == "grayscale"
        and product["tiles"]["pixel_type"] == "uint8"
        and product["target"]["bounds"] == [-180.0, -90.0, 180.0, 90.0],
        "Product differs from the lunar publication contract",
    )
    records = {}
    for relative in ["evidence/preflight.json", "evidence/tiles.validation.json"]:
        records[relative] = read_json(run_root / relative)
    for folder, pattern in (
        ("evidence/sources", "*.json"),
        ("work/state", "*.json"),
        ("source", "*.tif.download.json"),
        ("logs", "*.log"),
    ):
        for path in sorted((run_root / folder).glob(pattern)):
            records[path.relative_to(run_root).as_posix()] = read_json(path)
    required = {
        "work/state/build-base.json",
        "work/state/emit-tiles.json",
        "work/state/validate-tiles.json",
    }
    required.update(
        f"work/state/build-level-{z}.json"
        for z in range(product["tiles"]["maximum_zoom"])
    )
    require(required <= records.keys(), "Missing stage evidence")
    require(
        all(records[name].get("status") == "complete" for name in required),
        "Incomplete stage",
    )
    producers = {}
    for identity in producer_identities([product, *records.values()]):
        require(
            identity.get("git_dirty") is False,
            "Evidence was generated by dirty producer code",
        )
        commit = identity.get("git_sha", "")
        require(
            re.fullmatch(r"[0-9a-f]{40}", commit) is not None,
            "Missing exact producer SHA",
        )
        if commit not in producers:
            require(
                code_tree_sha256(producer_root, commit) == identity["code_tree_sha256"],
                "Recorded producer code identity differs from committed code",
            )
        else:
            require(
                producers[commit] == identity,
                "Conflicting identities for one producer commit",
            )
        producers[commit] = identity
    build_commit = records["work/state/build-base.json"]["identity"]["producer"][
        "git_sha"
    ]
    semantic_project = records["work/state/build-base.json"]["identity"]["project"]
    canonical = lambda value: hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()
    require(
        canonical(semantic_project) == product["project_identity_sha256"],
        "Recorded project identity mismatch",
    )
    require(
        records["work/state/validate-tiles.json"]["report_sha256"]
        == sha256(run_root / "evidence/tiles.validation.json"),
        "Validation report changed",
    )
    require(
        records["work/state/emit-tiles.json"]["output"]["product_json_sha256"]
        == sha256(output / "product.json"),
        "Tile-emission product changed",
    )
    require(
        canonical(
            {
                "project": semantic_project,
                "source_sha256": [item["sha256"] for item in product["sources"]],
                "target_crs_sha256": product["target"]["crs_sha256"],
                "producer": product["producer"],
                "tools": product["tools"],
                "manifest_set_sha256": product["manifest_set_sha256"],
            }
        )
        == product["product_identity_sha256"],
        "Product semantic identity mismatch",
    )
    source_spec = tomllib.loads(
        subprocess.check_output(
            ["git", "-C", str(producer_root), "show", f"{build_commit}:{SOURCE_PATH}"]
        ).decode()
    )
    source = run_root / "source" / source_spec["filename"]
    expected = source_spec["expected"]
    require(source_spec["status"] == "admitted", "Source is not admitted")
    require(
        source.stat().st_size == expected["size_bytes"]
        and sha256(source) == expected["sha256"],
        "Source payload differs from admitted source",
    )
    require(
        product["sources"][0]["sha256"] == expected["sha256"],
        "Product source identity mismatch",
    )
    levels = verify_tiles(output, product, validation)
    staging = Path(
        tempfile.mkdtemp(prefix="lunar-publication-", dir=destination.parent)
    )
    try:
        exports = []
        for relative, value in records.items():
            portable_value = portable(value, run_root, producer_root)
            exported_role = relative.removeprefix("evidence/")
            target = staging / "evidence" / exported_role
            write_json(target, portable_value)
            exports.append(
                {
                    "source_role": relative,
                    "original_sha256": sha256(run_root / relative),
                    "published_path": target.relative_to(staging).as_posix(),
                    "published_sha256": sha256(target),
                    "transformation": "portable-json",
                }
            )
        shutil.copytree(output / "manifests", staging / "payload/manifests")
        shutil.copyfile(output / "product.json", staging / "payload/product.json")
        for name in (PROJECT_PATH, SOURCE_PATH, *CRS_PATHS, "LICENSE"):
            path = staging / "reproduction/producer" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(
                subprocess.check_output(
                    ["git", "-C", str(producer_root), "show", f"{build_commit}:{name}"]
                )
            )
            if name == CRS_PATHS[0]:
                require(
                    sha256(path) == product["target"]["crs_sha256"],
                    "Target CRS changed",
                )
        for commit in sorted(producers):
            for name in ("pyproject.toml", "uv.lock"):
                path = staging / "reproduction/software" / commit / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(
                    subprocess.check_output(
                        ["git", "-C", str(producer_root), "show", f"{commit}:{name}"]
                    )
                )
        write_json(
            staging / "evidence/export_inventory.json",
            {
                "format_version": 1,
                "assembly_commit": assembly_commit,
                "path_tokens": {
                    "${RUN_ROOT}": "original run directory",
                    "${PRODUCER_ROOT}": "producer checkout root",
                },
                "records": exports,
            },
        )
        write_json(
            staging / "evidence/assembly_verification.json",
            {
                "format_version": 1,
                "verified_at": datetime.now(UTC).isoformat(),
                "assembly_commit": assembly_commit,
                "source_sha256": expected["sha256"],
                "source_bytes": expected["size_bytes"],
                "tile_count": product["tiles"]["total_count"],
                "tile_bytes": product["tiles"]["total_bytes"],
                "source_and_all_tile_bytes_rehashed": True,
                "project_and_product_identities_recomputed": True,
                "producer_code_trees_recomputed_from_recorded_commits": True,
                "pixel_reconstruction": "authenticated-producer-report; not rerun by assembler",
            },
        )
        prefix = f"textures/moon/lroc-wac-global-100m/{release}/"
        readiness = {
            "format_version": 1,
            "publication_ready": False,
            "completed": {
                "recorded_producer_trees_authenticated": True,
                "admitted_source_rehashed": True,
                "every_tile_rehashed": True,
                "producer_pixel_validation_recorded": True,
                "portable_evidence_exported": True,
            },
            "pending": {
                "public_producer_commits": "Publish and verify every recorded producer commit; no producer remote is configured in this preparation checkout.",
                "historical_runtime": "Historical Python version is not recorded; do not substitute the assembly interpreter version.",
                "pinned_gdal_proj_environment": "Recorded GDAL/PROJ versions do not pin a distribution or container. Establish a replayable environment and verify reproduction before finalizing this payload.",
                "upstream_reuse_terms": "Confirm and record product-specific imagery reuse terms; a USGS hosting URL alone does not establish copyright status.",
                "consumer_acceptance": "Record viewer acceptance at poles, antimeridian, tile joins, and zoom transitions.",
                "immutable_hosting": "Upload this exact product and verify remote checksums, object metadata, CDN delivery, and CORS; retain a generated receipt.",
                "zenodo_deposit": "Reserve the initial Version DOI, confirm metadata and actual publication date, and assemble the final deposit from a clean public catalogs commit.",
            },
        }
        write_json(staging / "evidence/publication_readiness.json", readiness)
        substitutions = {
            "RELEASE": release,
            "DATE": f"{release[:4]}-{release[4:6]}-{release[6:8]}",
            "TITLE": TITLE,
            "SERIES": SERIES,
            "PREFIX": prefix,
            "IDENTITY": product["product_identity_sha256"],
            "ASSEMBLY_COMMIT": assembly_commit,
            "TILE_COUNT": f"{product['tiles']['total_count']:,}",
            "TILE_BYTES": f"{product['tiles']['total_bytes']:,}",
            "BUILD_COMMIT": build_commit,
            "TILE_COMMIT": product["producer"]["git_sha"],
            "LEVEL_TABLE": "\n".join(
                f"| {row['zoom']} | {row['count']:,} | {row['bytes']:,} |"
                for row in levels
            ),
        }
        for template in sorted((repository / "templates/lunar_texture").rglob("*")):
            if template.is_file():
                target = staging / template.relative_to(
                    repository / "templates/lunar_texture"
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                text = template.read_text(encoding="utf-8")
                for name, value in substitutions.items():
                    text = text.replace(f"@{name}@", value)
                require(not re.search(r"@[A-Z_]+@", text), "Unexpanded template token")
                target.write_text(text, encoding="utf-8")
        manifest = {
            "format_version": 1,
            "release": release,
            "series_id": SERIES,
            "title": TITLE,
            "status": "draft",
            "publication_model": "evolving-versioned-series",
            "lifecycle": {
                "release_snapshot": "immutable",
                "zenodo_relationship": "initial-record",
                "later_versions": "zenodo-new-version",
                "doi_status": "not-reserved",
            },
            "payload": {
                "product_id": product["product_id"],
                "product_identity_sha256": product["product_identity_sha256"],
                "product_json": "payload/product.json",
                "product_json_sha256": sha256(output / "product.json"),
                "manifest_set_sha256": product["manifest_set_sha256"],
                "tile_count": product["tiles"]["total_count"],
                "tile_bytes": product["tiles"]["total_bytes"],
                "tiles_in_git_or_metadata_deposit": False,
                "storage_status": "planned-not-uploaded",
                "intended_s3_bucket": "foundinspace",
                "intended_s3_prefix": prefix,
                "intended_cdn_base_url": f"https://data.foundin.space/{prefix}",
                "content_type": "image/png",
                "cache_control": "public, max-age=31536000, immutable",
            },
            "source": {
                "landing_page": SOURCE_PAGE,
                "filename": source_spec["filename"],
                "sha256": expected["sha256"],
                "size_bytes": expected["size_bytes"],
                "reuse_terms_status": "pending-product-specific-confirmation",
            },
            "provenance": {
                "assembly_repository": "https://github.com/Found-in-Space/catalogs",
                "assembly_commit": assembly_commit,
                "assembly_python_version": sys.version.split()[0],
                "assembly_imports_producer": False,
                "build_commit": build_commit,
                "tile_emission_and_validation_commit": product["producer"]["git_sha"],
                "intended_producer_repository": PRODUCER_URL,
                "producer_public_access_status": "not-verified",
                "historical_python_version_status": "not-recorded",
                "gdal": product["tools"]["gdal"],
                "proj": product["tools"]["proj"],
                "toolchain_distribution_status": "not-pinned",
                "export_inventory": "evidence/export_inventory.json",
                "readiness": "evidence/publication_readiness.json",
            },
            "license": {
                "found_in_space_original_metadata": "CC-BY-4.0",
                "upstream_imagery": "pending-product-specific-confirmation",
                "producer_software": "MIT",
            },
        }
        lines = []
        for key, value in manifest.items():
            if not isinstance(value, dict):
                lines.append(f"{key} = {json.dumps(value)}")
        for section, fields in manifest.items():
            if isinstance(fields, dict):
                lines.extend(["", f"[{section}]"])
                lines.extend(
                    f"{key} = {json.dumps(value)}" for key, value in fields.items()
                )
        for row in levels:
            lines.extend(["", "[[levels]]"])
            lines.extend(f"{key} = {json.dumps(value)}" for key, value in row.items())
        for commit, identity in sorted(producers.items()):
            lines.extend(
                [
                    "",
                    "[[producer_commits]]",
                    f'git_sha = "{commit}"',
                    f'code_tree_sha256 = "{identity["code_tree_sha256"]}"',
                    "git_dirty = false",
                    f'package_version = "{identity["package_version"]}"',
                ]
            )
        (staging / "manifest.toml").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        tomllib.loads((staging / "manifest.toml").read_text())
        regenerate_checksums(staging)
        staging.rename(destination)
        return {
            "release": release,
            "tile_count": product["tiles"]["total_count"],
            "tile_bytes": product["tiles"]["total_bytes"],
            "publication_ready": False,
            "producer_commits": sorted(producers),
        }
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--producer-root", type=Path, required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    arguments = parser.parse_args()
    print(
        json.dumps(
            prepare(
                run_root=arguments.run_root.resolve(),
                producer_root=arguments.producer_root.resolve(),
                release=arguments.release,
                destination=arguments.destination.resolve(),
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
