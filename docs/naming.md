# Naming

Names should be boring, stable, lowercase, and easy to sort.

## Publication Releases

Publication releases use a date plus release number:

```text
20260515.1
20260515.2
20260516.1
```

The date is `YYYYMMDD`. The number after the dot is the release sequence for
that date. Start each day at `.1`.

Use a new release number whenever a separate product is published or an
existing publication changes. Do not reuse one release ID for separate
products.

## First Planned Releases

- `20260515.1` - first clean mag-11 build publication.
- `20260515.2` - first Gaia-HIP crossmatch publication.

The details of each publication belong in that publication's own README and
manifest.

## Files

Use snake case for file stems:

```text
manifest.toml
quality_report.json
```

Prefer names that describe what the file is to a reader, not the temporary
pipeline step that produced it.
