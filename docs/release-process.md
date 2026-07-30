# Release Process

This is the minimal release checklist. Each publication can add its own
procedure inside `publications/<release>/README.md`.

## Choose the Publication Relationship

Before creating a release, decide whether it is:

- a new standalone work, which receives a new Zenodo record and Concept DOI;
  or
- a new immutable snapshot of an existing evolving series, which must use
  Zenodo's **New version** action in the existing record lineage.

Record that decision and a stable `series_id` in the manifest. Never create a
second independent Zenodo record for a revision of the same evolving catalog.
An unpublished repository candidate is not a Zenodo version and does not start
a DOI lineage.

## DOI and Immutability Rules

Every published release is immutable. Changes to data, evidence, checksums,
selection rules, or methodology require a new release directory. For an
evolving series, publish that release as **New version** in the same Zenodo
lineage.

Zenodo assigns a distinct Version DOI to each published snapshot and one stable
Concept DOI to the version chain. Cite the Version DOI for reproducible work
that depends on exact inputs. Cite the Concept DOI for the series as a whole or
when intentionally resolving to the latest release.

A metadata-only correction may edit a published record only when the payload
and its scientific interpretation remain unchanged. If there is doubt, create
a new version.

## Release Checklist

1. Choose the next release ID.
2. Create `publications/<release>/`.
3. Add a README explaining the publication, lifecycle, and citation policy.
4. Add a manifest recording the series, lifecycle, important inputs, outputs,
   decisions, and provenance.
5. Keep local scratch paths, credentials, and raw source dumps out of the
   publication.
6. If the publication includes counts, artifact metadata, or checksums,
   generate them from the final files. Do not hand-edit generated records.
7. Add Zenodo draft metadata and state whether this is an initial deposit or a
   new version in an existing lineage.
8. Verify the publication can be understood from its directory alone.
9. Commit and publish the exact release content to the public repository.
10. Build and validate the deposit payload from a clean checkout of that exact
    public commit.
11. Publish through the chosen Zenodo lineage.
12. Record the Version DOI, Concept DOI, public commit, and deposited-file
    checksum as post-publication tracking metadata. Do not add this tracking
    file to the already-published payload or its checksum manifest.

Official Zenodo guidance:

- <https://help.zenodo.org/docs/deposit/manage-versions/>
- <https://help.zenodo.org/docs/deposit/manage-files/>
- <https://zenodo.org/help/versioning>

The first clean sequence is expected to be:

- `20260515.1` - first clean mag-11 build publication.
- `20260515.2` - first Gaia-HIP crossmatch publication.
