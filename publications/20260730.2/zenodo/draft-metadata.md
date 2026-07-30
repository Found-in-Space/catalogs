# Zenodo Publication Metadata and Version Workflow

This file is preparation material for the initial Zenodo deposit of
`fis.overrides`. It records the required metadata and the lifecycle that later
releases must follow. It does not contain a reserved or assigned DOI.

## Record Metadata

- Title: **Found in Space stellar overrides**
- Upload type: **Dataset**
- Version: **20260730.2**
- Publication date: set to the actual publication date
- Creator: **Siebert, Kaj Wik**
- Affiliation: **University College London**
- ORCID: **0009-0009-4500-4316**
- Community: **Found in Space**
- Licence: **Creative Commons Attribution 4.0**

Suggested keywords:

- stellar catalogues
- Gaia DR3
- Hipparcos
- astrometry
- photometry
- distance overrides
- reproducible data
- 3D visualization

## Description

`fis.overrides` is an evolving, versioned catalog of explicit stellar
replacements for controlled Found in Space data builds. Release `20260730.2`
is a cumulative immutable snapshot containing 51 `replace` actions: the three
original Alpha Centauri overrides and 48 reviewed distance replacements.

The release excludes 33 provisional review rows, the retired Sirius B and
Procyon B overrides, and the Sun. It preserves the published Gaia DR3
`hipparcos2_best_neighbour` table as the only automatic Gaia-Hipparcos pairing
authority and does not apply the supplemental pairing map.

Every executable row has row-level provenance and passes the 19 checks recorded
in `evidence/override_quality_report.json`. The publication also contains the
historical three-row source, compact review evidence, build reports, exact
public code commits, and SHA-256 checksums.

Every published release in this catalog is immutable. Changes to catalog data,
evidence, checksums, selection rules, or methodology are issued with Zenodo's
**New version** action in this same record lineage.

## DOI and Citation Policy

The initial publication assigns:

- a Version DOI for the immutable `20260730.2` snapshot; and
- a Concept DOI that remains stable across all versions of `fis.overrides`.

Use the Version DOI for reproducible work tied to this exact release. Use the
Concept DOI for the evolving catalog series or when intentionally following
the latest published version. Do not invent either value before Zenodo assigns
it.

Suggested citation after publication:

> Siebert, K. W. (2026), *Found in Space stellar overrides*, version
> 20260730.2, Zenodo, `<VERSION_DOI>`.

## Initial Publication Procedure

No earlier `fis.overrides` record exists in Zenodo. For `20260730.2`:

1. Merge the release commit into the public catalogs repository.
2. From a clean checkout of that exact public commit, run the assembler, full
   tests, and `sha256sum --check checksums.sha256`.
3. Create a path-preserving release archive outside
   `publications/20260730.2/`; do not place the archive inside the checksummed
   payload.
4. Create a new Zenodo upload, enter the metadata above, and upload the release
   archive. This is the one time a new Zenodo record is created for this
   series.
5. Verify the previewed file, title, version, creator, licence, description,
   and checksums before selecting **Publish**.
6. After publication, record the assigned record ID, Version DOI, Concept
   record ID, Concept DOI, publication URL, release commit, and archive
   checksum in `zenodo/published-record.toml`.
7. Treat `zenodo/published-record.toml` as post-publication repository tracking
   metadata. Do not add it to the already-published archive or to that
   snapshot's `checksums.sha256`.

## Procedure for Every Later Catalog Revision

1. Create a new immutable repository release directory and carry forward the
   complete intended catalog state.
2. Re-run all provenance, quality, deterministic-build, and checksum checks.
3. Open the current `fis.overrides` Zenodo record and select **New version**.
4. Replace the files with the new release archive and update the Version,
   description, change notes, and publication date.
5. Publish only after verifying the new snapshot. Zenodo will assign a new
   Version DOI while retaining the same Concept DOI.
6. Record both identifiers and the exact public commit in the new release's
   post-publication tracking metadata.

A metadata-only correction may use Zenodo's edit-record workflow only when the
payload and its scientific interpretation remain unchanged. Any ambiguity
about whether a change is substantive must be resolved in favor of a new
version.

Official Zenodo guidance:

- <https://help.zenodo.org/docs/deposit/manage-versions/>
- <https://help.zenodo.org/docs/deposit/manage-files/>
- <https://zenodo.org/help/versioning>
