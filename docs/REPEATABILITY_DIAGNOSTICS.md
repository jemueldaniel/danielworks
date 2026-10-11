# Repeatable public-profile diagnostic receipts

This independently authored utility diagnoses intermittent failures in the existing publicly reproducible engineering kit. It does not import private repositories, accept arbitrary manifest commands, or claim production certification.

It separately executes each fixed public test profile against an already-exported, externally SHA-256-pinned starter. Each run checks that source and output bytes remain unchanged, records the allowlisted profile name and an intentionally redacted status/error code, and writes an exclusive acceptance receipt outside the source and output folders.

## Run

From an exact published public checkout, after completing the normal source-pinned one-shot export, run:

    python -B tools/diagnose_public_profiles.py --destination ../public-kit --expected-manifest-sha256 EXTERNAL_EXPORT_MANIFEST_SHA256 --rounds 2 --receipt ../public-profile-diagnostics.json

Use the exported REUSE_MANIFEST.json SHA-256, **not** the source repository's SOURCE_MANIFEST.json SHA-256. The destination must already contain a verified public starter, and the receipt path must not exist. For one profile, add --profile followed by its existing allowlisted public name.

The default is two explicit diagnostic rounds; the limit is three rounds and each test group has a bounded timeout. Failures remain recorded even if later runs pass. Any missing, changed, linked, or unexpected public output aborts integrity qualification. Output does not echo private environment variables, stdout/stderr, exception messages, absolute local paths, or credential material. The child runner uses the minimal environment already defined by the original public one-shot assembler.

The helper's own deterministic tests can be run with:

    python -B -m unittest discover -s tools -p test_diagnose_public_profiles.py -v

Its unit tests simulate both success and intentionally forged or failing group results, post-test modification, existing receipts and sensitive exception messages. Mocked tests do not verify live Windows socket stability or certify whole-package security.

A PASS_REPEATED receipt is evidence only that the specified public local tests passed in the requested environment and rounds. FAIL_RECORDED stays failed, regardless of later passing runs. Publication, authorship, legal rights, real cloud infrastructure, distributed execution and production behavior require independent qualification.
