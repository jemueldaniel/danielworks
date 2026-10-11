# Public-only one-command project starter

This is a **portable reuse exercise**, not an employer or startup source export.
It assembles *only existing public, self-contained examples* from the currently
pinned DanielWorks snapshot. Source is never fetched from a network or copied
from private repositories, local product checkouts, environment files, or
third-party assets.

## Generate a starter

Run from a clean DanielWorks checkout, using the current `SOURCE_MANIFEST.json`
SHA-256 from a separately verified publication receipt. Do **not** use a hash
copied solely from inside the checkout as an authenticity proof.

```sh
python -B tools/export_public_starter.py \
  --expected-manifest-sha256 YOUR_EXTERNAL_64_CHARACTER_SHA256 \
  --profile agent --profile training \
  --destination ../new-public-engineering-starter
```

The destination **must not exist**. Source is checked against the pinned
manifest and public claim index, then copied byte-for-byte. All output file
names and hashes are recorded in `REUSE_MANIFEST.json`. No installs, build,
cloud deploys, external requests, token reads or tests run during export.
The generated `README.md` lists the tests you should execute afterward.

Profiles: `agent`, `jobs`, `training`, `retrieval`, `evaluation`, `typed-api`,
`rust-compiler`. The first five are currently marked *executed* in the source
capability map. The final two are *historical* and require `--allow-historical`.
`--all-executed` bundles all five executed profiles, and `--dry-run` checks
source and lists proposed work without writing a destination.

## Employment use and limits

1. Start with the employer's desired behavior, threat model, operational SLOs,
   data classification and existing stack rather than imposing a favorite tool.
2. Choose a **public pattern**, check its tests and license/ownership, then
   adapt the *idea* and rewrite project-specific integration code.
3. Keep secrets, proprietary endpoints, customer data and internal architecture
   out of public tickets, prompts, generated manifests and demonstrations.
4. Re-run current platform tests, accessibility/security checks, dependency
   reproducibility and real deployment acceptance in the **new environment**.
5. Save revision, exact commands, checksums, observed failures and reviewer
   verdicts; do not inherit the sample's qualification claim automatically.

The starter is **not** production security clearance, licensed redistribution
permission, current-browser certification, real EVM settlement, native WebMCP,
full-scale training, enterprise PostgreSQL, or proof of sole human authorship.
No attempt is made to run private repositories or reconstruct closed-source work.

**Windows note:** Creating symbolic links for negative tests may require Developer Mode
or elevated privilege. Such tests report a skip when that privilege is denied;
they are never counted as a pass. The actual source verifier has separate NTFS
reparse-point checks. The Node agent test uses the TAP reporter to avoid
platform-dependent pretty-print output.
