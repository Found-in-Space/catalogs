# Run Log

Release: `20260630.1`

This log records the creation of the metadata-only Gaia download provenance
publication wrapper.

## Environment

- Meta-repo working directory: `/home/kws/work/fis`
- Catalog repository: `catalogs/`
- Pipeline repository: `pipeline/`
- Existing source package:
  `pipeline/data/packages/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038`
- Publication directory: `catalogs/publications/20260630.1`
- Execution date: `2026-06-30`

## Source Package

The publication wraps the already-created local download package:

```text
fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038
```

The package records:

- pipeline git HEAD `3e64bfe97038b4f62395601a2ccc6bca7ad44556`;
- clean tracked pipeline worktree at packaging time;
- acquisition spec hash
  `b4db1f05d67e4deb38a91c9547ea7a38c33b93ad26c9d0cd326ad198efcebd47`;
- `60` raw VOTable gzip payload files;
- `146,842,060,166` raw payload bytes;
- `1,467,744,818` selected Gaia rows;
- complete raw payload SHA-256 manifest.

## Steps Executed

1. Confirmed the publication release ID.

   Existing catalog publication IDs were:

   ```text
   20260515.1
   20260517.1
   ```

   This publication uses `20260630.1`.

2. Verified local source package facts.

   ```bash
   du -sh pipeline/data/packages/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038
   find pipeline/data/packages/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038 -maxdepth 4 -type f | wc -l
   ```

   Result:

   - Full local package size: `137G`.
   - Package file count including raw payload and query files: `307`.
   - Query bundle file count: `225`.

   These values exceed the intended normal Zenodo upload shape if raw files or
   query files are uploaded individually.

3. Copied small reader-facing evidence files into the publication directory.

   Copied from the local package:

   - `evidence/gaia-download-state-summary.json`
   - `evidence/gaia-download-batches.json`
   - `manifests/gaia-download-queries-manifest.tsv`
   - `manifests/gaia-votables-manifest.tsv`
   - `manifests/gaia-votables.sha256`
   - `manifests/package-control.sha256`
   - `manifests/supporting-files.sha256`
   - `manifests/checksum-status.txt`

4. Created the Zenodo metadata archive.

   The archive was built from the local package with `payload/` excluded:

   ```bash
   rsync -a --exclude payload \
     pipeline/data/packages/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038/ \
     <temporary-staging>/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038/
   tar -C <temporary-staging> -czf \
     catalogs/publications/20260630.1/zenodo/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038-metadata.tar.gz \
     fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038
   ```

   Result:

   - Archive size: `120,274` bytes.
   - Archive entry count: `253`.
   - Raw `payload/` entries: `0`.
   - Archive SHA-256:
     `71b7e7fae684286646ac060b02edbe4ae082eb865efdc0182ee432657056ae02`.

5. Added publication metadata.

   Created:

   - `README.md`
   - `manifest.toml`
   - `run_log.md`
   - `LICENSE.txt`
   - `NOTICE.md`
   - `REFERENCES.md`

6. Generated final publication checksums.

   `checksums.sha256` was generated from the final publication files, excluding
   only the path-preserving Zenodo upload ZIP wrapper.

7. Recorded the reserved Zenodo DOI.

   Reserved version DOI:

   ```text
   10.5281/zenodo.21066981
   ```

   Draft record URL:

   ```text
   https://zenodo.org/records/21066981
   ```

8. Switched the Zenodo upload shape to a path-preserving ZIP plus loose README.

   Zenodo upload files:

   - `README.md`
   - `zenodo/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038-publication.zip`

   The publication ZIP preserves the nested `evidence/` and `zenodo/` paths.
   It is not included in `checksums.sha256`, because that would make the
   checksum manifest self-referential.

## Zenodo Notes

The Zenodo upload should remain metadata/control-only. The raw Gaia VOTable
gzip payload is inventoried and checksummed by this publication but intentionally
omitted from the upload.

The reserved Zenodo version DOI is `10.5281/zenodo.21066981`. The concept DOI is
not recorded yet; add it after Zenodo exposes it for the published/versioned
record.
