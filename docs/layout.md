# Repository Layout

The durable unit in this repository is a publication.

```text
publications/
  <release>/
    README.md
    manifest.toml
    ...

docs/
schemas/
src/
templates/
tests/
```

`publications/<release>/` is where a reader should start. Each publication
decides for itself what files it needs: data, configs, evidence, reports,
generated counts, checksums, or something else.

A release directory becomes an immutable snapshot when published. An evolving
catalog uses a new adjacent release directory for each revision and records the
same stable series identity in every manifest. The corresponding Zenodo
deposits remain in one version chain.

Do not split one publication across top-level folders by artifact type. If a
publication needs supporting evidence, put that evidence inside the
publication.

## Top-Level Directories

`publications/` contains citable data publications.

`docs/` contains repository housekeeping only.

`schemas/` contains shared schemas when we have stable formats worth
formalizing.

`templates/` contains minimal starter files. Copy from real prior publications
once we know what is useful.

`src/` and `tests/` contain local maintenance tooling.

Post-publication Zenodo tracking metadata may be stored as
`zenodo/published-record.toml` inside the release directory for repository
bookkeeping. Because the identifiers do not exist until publication, that file
is not part of the deposited payload or its `checksums.sha256`.

## Do Not Store

- Full raw source catalogues.
- Full generated payloads unless we explicitly decide a publication includes
  them.
- Machine-specific absolute paths in public manifests.
- Credentials, tokens, private download URLs, or local environment files.
- Large scratch outputs that are not explained by a publication.
