# Exact dependencies and licenses

The following versions and license identifiers were read from the installed packages used for the Windows verification, not guessed from import statements. Packages are fetched separately; dependencies and built bundles are not vendored in this source archive.

| Direct package | Tested version | Declared package license |
|---|---|---|
| `@modelcontextprotocol/sdk` | 1.32.1 | MIT |
| `react` | 19.3.0 | MIT |
| `react-dom` | 19.3.0 | MIT |
| `zod` | 4.6.5 | MIT |
| `@types/node` | 26.6.4 | MIT |
| `@types/react` | 19.3.0 | MIT |
| `@types/react-dom` | 19.3.0 | MIT |
| `esbuild` | 0.28.2 | MIT |
| `playwright` | 1.63.0 | Apache-2.0 |
| `typescript` | 7.0.2 | Apache-2.0 |

Full transitive resolution and integrity values are pinned by `package-lock.json` (npm lockfile version 3). Lock SHA-256:

```text
f389c35e449bc42227cd3113c0d14c948d82a9bd1fa97a455c8a4c273c2a9731
```

The [captured package metadata](../verification/versions.json) and [dependency audit](../verification/dependency-audit.json) accompany this candidate. Declared licenses are metadata, not an independent legal audit. Check transitive licenses and preserve required notices before distributing a built bundle. No third-party copyright or license is reassigned to the repository owner.

## Runtime qualification

The new workbench was tested with Node 24.15.0, npm 11.13.0, Python 3.13.6, SQLite 3.50.4 and Edge 154.0.4258.53. Python backend checks also ran with Python 3.13.5/SQLite 3.46.1. The original unchanged example runner used Node 22.16.0 and TypeScript 5.8.3 in that Linux environment. These are separate verified combinations; do not infer that every cross-combination has passed.

The Node type package is version 26.6.4 but the executed runtime is Node 24.15.0. Only the APIs exercised here are qualified; installing newer declarations does not make newer runtime APIs available. The root `engines` floor is a source constraint, not additional execution evidence.

The official MCP SDK used here supports the selected 2025-11-25 protocol. This candidate deliberately tests that version; it does not claim to use the newest MCP specification or every supported protocol feature.

## Installation and boundaries

Use the lockfile with `npm ci --ignore-scripts --no-audit --no-fund`; the exact bounded command and exit status are recorded in [TEST_EVIDENCE.md](TEST_EVIDENCE.md). Python uses only the standard library, including SQLite with FTS5. Browsers are not downloaded automatically. No credentials are required for the synthetic loopback profiles.

No root software license was chosen or existing material relicensed in this batch. The owner has already authorized public source publication; choosing an additional umbrella grant of reuse rights is a separate decision, not a request to repeat publication permission. Unapproved third-party or private source is excluded, and dependency obligations remain applicable. [Provenance and assistance disclosure](PROVENANCE.md).
