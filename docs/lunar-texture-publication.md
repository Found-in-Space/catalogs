# Preparing the first lunar texture publication

`scripts/prepare_lunar_publication.py` authenticates the existing controlled
LROC WAC product and assembles a draft metadata publication. It does not run
the raster producer, rebuild images, upload objects, or publish a Zenodo record.
It uses only Python's standard library, so no producer path dependency or
editable package import participates in metadata assembly.

The script must run from a clean checkout of a catalogs commit already pushed
to its public remote. It reads producer code and configuration from the exact
Git objects recorded in build evidence. Dirty producer evidence and dirty
producer checkouts are rejected. Anonymous public producer access and the
exact USGS product's public-domain reuse metadata are verified during assembly.
Representative checks and immutable hosting are recorded from the public
scripts' generated reports with `--sample-report` and `--hosting-receipt`.
Viewer acceptance and DOI deposit remain explicit pending steps.

For display textures, preserve the recorded process and uv lockfiles, record
native GDAL/PROJ versions, and check representative spatial and visual results.
A hermetic OS image, identical regenerated PNG bytes, and a full independent
pyramid rebuild are not publication requirements. Payload checksums continue
to authenticate the published files and protect transfers.

`scripts/publish_lunar_tiles.py` uses the locked `publication` dependency group.
Its default dry run inventories the exact tile tree, manifests, and descriptor.
`--publish --profile <aws-profile> --receipt <new-receipt.json>` performs
conditional S3 writes, resumes matching objects, verifies every checksum and
delivery metadata, and publishes the descriptor last. It then verifies the
exact remote inventory and representative full CDN responses and CORS.
Uploads default to four connections and a shared 1 MiB/s payload budget.
Adjust `--max-upload-mibps` and `--workers` explicitly when another network
budget is appropriate; retries share the same bandwidth limit.

Choose the next free `YYYYMMDD.N` release, then run from that clean checkout:

```bash
uv run --no-project python scripts/prepare_lunar_publication.py \
  --run-root /path/to/controlled-run \
  --producer-root /path/to/clean-producer-checkout \
  --release YYYYMMDD.N \
  --destination /path/to/catalogs/publications/YYYYMMDD.N
```

Source and tile bytes are streamed through SHA-256. Four tile readers have at
most eight pending hashes; only one level's tile addresses are tracked in memory.
The script cross-checks producer metadata,
stage states, manifests, source admission, and committed code identities.
It refuses an existing destination and places the candidate atomically after
the evidence export and checksum manifest are complete.

The generated publication contains `PUBLISHING.md` and its own reproduction,
interpretation, licensing, hosting, and citation instructions. Never edit
generated counts or reports by hand. Finalization requires reviewed evidence
for each remaining gate and a new clean public release commit.
