# Release Process

This is the minimal release checklist. Each publication can add its own
procedure inside `publications/<release>/README.md`.

1. Choose the next release ID.
2. Create `publications/<release>/`.
3. Add a README explaining what the publication is.
4. Add a manifest recording the important inputs, outputs, decisions, and
   provenance.
5. Keep local scratch paths, credentials, and raw source dumps out of the
   publication.
6. If the publication includes counts, artifact metadata, or checksums,
   generate them from the final files. Do not hand-edit generated records.
7. Verify the publication can be understood from its directory alone.
8. Commit the publication and housekeeping changes intentionally.

The first clean sequence is expected to be:

- `20260515.1` - first clean mag-11 build publication.
- `20260515.2` - first Gaia-HIP crossmatch publication.
