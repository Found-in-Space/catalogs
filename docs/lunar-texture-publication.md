# Preparing the first lunar texture publication

`scripts/prepare_lunar_publication.py` authenticates the existing controlled
LROC WAC product and assembles a draft metadata publication. It does not run
the raster producer, rebuild images, upload objects, or publish a Zenodo record.
It uses only Python's standard library, so no producer path dependency or
editable package import participates in metadata assembly.

The script must run from a clean checkout of a catalogs commit already pushed
to its public remote. It reads producer code and configuration from the exact
Git objects recorded in build evidence. Dirty producer evidence and dirty
producer checkouts are rejected. Missing public producer access, environment
pinning, imagery rights, viewer acceptance, hosting, and DOI steps remain
explicit gates rather than being inferred from successful tile validation.

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
