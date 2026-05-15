# Release Process

This process is for public catalogue releases from this repository.

## Before Release

1. Choose a catalogue release, for example `20260515.1`.
2. Ensure every versioned catalogue directory has a `manifest.toml`.
3. Validate override IDs are unique.
4. Validate supplemental crossmatches are one-to-one.
5. Run the pipeline build using the versioned configs.
6. Run the octree build if the release includes octree build records.
7. Write post-build counts and checksums.
8. Confirm no local absolute paths, credentials, or scratch logs are included.
9. Update `CITATION.cff` and `.zenodo.json` if present.
10. Tag and create a GitHub release.

## Zenodo

For now, Zenodo should archive the catalog repository release. The release
records exact upstream git SHAs for pipeline and octree code, but does not
vendor that source code.

Use the version DOI for reproducibility in papers and build metadata. Use the
concept DOI when referring to the evolving catalogue project as a whole.

## Release Notes

Release notes should summarize:

- new or changed overrides
- new or changed supplemental crossmatches
- source catalog releases
- build IDs included
- known limitations
- citation and acknowledgement notes
