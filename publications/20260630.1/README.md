# Gaia DR3 Full Download Provenance

Release: `20260630.1`

This publication records the acquisition provenance for the Found in Space Gaia
DR3 full download used by the controlled core dataset work. It is a
metadata/control publication, not a republication of the Gaia source payload.

The raw Gaia VOTable gzip files total `146,842,060,166` bytes across `60`
files. They are inventoried and checksummed here, but they are intentionally
not included in the Zenodo upload payload.

## Purpose

Downstream Found in Space publications should cite this release as the Gaia
download base. It pins:

- the exact pipeline commit used to package the acquisition;
- the Gaia Archive ADQL query bundle;
- the downloader state summary and per-batch state;
- source payload filenames, byte sizes, and checksums;
- dependency and configuration context.

The source publication files are maintained in the Found in Space catalogs
repository: <https://github.com/Found-in-Space/catalogs>.

## Zenodo Upload Shape

The intended Zenodo record should upload two files:

- `README.md`
- `zenodo/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038-publication.zip`

The ZIP preserves the publication paths shown in `checksums.sha256`, including
the nested `evidence/` and `zenodo/` files. Uploading `README.md` separately
allows Zenodo to preview the human-readable summary.

The publication ZIP is a transport wrapper for Zenodo upload. It is not listed
inside `checksums.sha256`, because that would make the checksum manifest
self-referential.

Inside the publication ZIP, the nested metadata archive:

- `zenodo/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038-metadata.tar.gz`

contains the package control tree, generated ADQL files, downloader SQLite state
database, manifests, checksums, and git provenance. It excludes the raw
`payload/gaia-votables/` files, so the upload remains comfortably below
Zenodo's default file-count and size limits.

## Key Facts

- Package ID: `fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038`
- Pipeline commit: `3e64bfe97038b4f62395601a2ccc6bca7ad44556`
- Pipeline tracked worktree clean at package time: `true`
- Gaia calculation engine: `dr3_ap_bj_core`
- Acquisition spec hash:
  `b4db1f05d67e4deb38a91c9547ea7a38c33b93ad26c9d0cd326ad198efcebd47`
- Count query hash:
  `dcda88ac871bcd121f915e77e8fa887def220fd7ed4c0e95708df61d6b6d57ee`
- Download query hash:
  `74b3d22969b65fa910adc6ce628b08135fd41fd4d1b2383ded7facba639fbb40`
- Downloaded batches: `60`
- HEALPix-3 count rows: `768`
- Source rows: `1,467,744,818`
- Downloaded bytes: `146,842,060,166`
- First downloaded batch: `2026-06-24T18:33:38+00:00`
- Last downloaded batch: `2026-06-27T04:35:45+00:00`

## Contents

- `manifest.toml` - release metadata, inputs, outputs, and Zenodo placeholders.
- `run_log.md` - command/procedure record for this publication wrapper.
- `checksums.sha256` - SHA-256 checksums for publication files.
- `evidence/gaia-download-state-summary.json` - exported downloader state
  summary.
- `evidence/gaia-download-batches.json` - exported per-batch downloader state.
- `evidence/gaia-download-queries-manifest.tsv` - query file inventory.
- `evidence/gaia-votables-manifest.tsv` - raw payload file inventory.
- `evidence/gaia-votables.sha256` - SHA-256 checksums for omitted raw payload
  files.
- `evidence/package-control.sha256` and `evidence/supporting-files.sha256` -
  local package checksum manifests.
- `zenodo/*-metadata.tar.gz` - metadata-only archive included inside the
  publication ZIP.

## Use

Use this publication to prove which Gaia Archive query bundle and downloader
state produced the raw Gaia input files for later Found in Space products. Do
not expect the Zenodo record to provide the raw Gaia payload. Rehydrate or audit
the raw payload from the upstream Gaia Archive and the checksums recorded here.

## DOI

Reserved Zenodo DOI: `10.5281/zenodo.21066981`

Draft record URL: <https://zenodo.org/records/21066981>

The Zenodo DOI is reserved in the draft record and will become registered when
the record is published. The concept DOI is not recorded here yet; add it after
Zenodo exposes it for the published/versioned record.
