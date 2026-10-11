# Processing and publication preparation record

Release: `20261011.1`  
Candidate preparation date: 2026-10-11

## Recorded build history

The evidence preserves the historical run rather than replacing it with one
current producer revision:

1. Acquisition used producer commit
   `1f657ce91eb795b2af7ec6169bdb2a61637605ac` and completed on 2026-10-02.
   The receipt records both the requested USGS URL and redirected public S3 URL,
   full source SHA-256, byte size, retrieval time, and the final range response.
   Its response `Content-Length` is the resumed segment length; `size_bytes`
   and the total in `Content-Range` describe the complete source.
2. Source inspection, admission, maximum-level reprojection, and lower-level
   raster construction used commit `56fd7a789cf31eea613d2f770a1042846090d587`.
3. Tile emission and complete pixel reconstruction validation used commit
   `deca93d4872bbbb3c75ccfa4083c9e865f331d86`. The later preflight report belongs to this revision too;
   it must not be described as a preflight preceding all historical processing.

Every recorded producer identity asserts a clean Git state. Preparation
recomputed its code-tree hash from the exact Git objects, including Python
source, `pyproject.toml`, and `uv.lock`. The manifest enumerates all revisions.
Pinned dependency files for each revision are included in `reproduction/software/`.

The producer reports GDAL 3.4.1 and PROJ 8.2.1. Product metadata also records
the `gdal_retile.py` checksum. The original Python interpreter version and a
pinned GDAL/PROJ distribution or container were not captured. Current machine
versions must not be substituted for that missing historical evidence.

## Evidence export

The assembler parses original JSON evidence and preserves complete command-output
logs as text in JSON wrappers, replacing the source-machine roots with
`${RUN_ROOT}` and `${PRODUCER_ROOT}`. The acquisition log retains the failed
timeout attempt preceding the successful resumed-download receipt.
Relative roles, command arguments, temporary filenames, timestamps, and
scientific metadata are retained. Unknown absolute paths and unreviewed URLs
are rejected. `evidence/export_inventory.json` records original and exported
file hashes, so the portability transformation is explicit. Exported evidence
has its own checksums; hashes referring to original evidence remain historical.

`payload/product.json`, tile manifests, project definitions, CRS resources,
and dependency files are copied byte for byte. No generated count, checksum,
validation flag, stage state, or product identity is hand-edited.

## Preparation validation

Assembler repository: `https://github.com/Found-in-Space/catalogs`  
Assembler commit: `0cebfd1ffaf914298a1b0aa2eeae98bd22cb8c21`

The assembler runs from a clean checkout of its pushed commit with Python's
standard library. It imports no local producer or pipeline package and uses
no path dependency, editable install, `PYTHONPATH`, or `sys.path` modification.
Its interpreter version is recorded separately from the unknown build version.

Preparation rehashed the admitted source and all 87,381 tiles; checked
their addresses, counts and byte sizes; authenticated the manifest set;
recomputed semantic project/product identities and committed producer code
identities; and checked the recorded validation and emission report hashes.
See `evidence/assembly_verification.json` for the verification timestamp.

The producer's complete pixel reconstruction validation is authenticated by
the checked product and tile hashes. The assembler does not repeat GDAL
reconstruction. No full rebuild, source redownload, S3 upload, viewer acceptance,
DOI reservation, or Zenodo publication is represented as completed.

## Finalization

Follow `PUBLISHING.md`. Preserve this candidate's recorded build history.
If reproducing it requires changed inputs, processing, or producer revisions,
create a new product identity and storage prefix instead of relabeling the old
payload. Generate final checksums and the deposit archive from the exact clean
public release commit. Post-publication DOI tracking is outside the deposit.
