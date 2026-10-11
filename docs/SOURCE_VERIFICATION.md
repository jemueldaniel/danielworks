# Verify restored source without modifying it

`tools/verify_source.py` verifies a quiet, isolated **source-only** checkout with Python's standard library. Run it before installing dependencies or building. It deliberately rejects unexpected dependency caches and generated files rather than silently hiding them. Normal top-level `.git` metadata is excluded and reported; repository source may not claim that metadata as payload.

```sh
python -B tools/verify_source.py --root .
python -B tools/verify_source.py --root . --expected-manifest-sha256 <trusted-64-character-lowercase-hash>
python -B -m unittest discover -s tools -p test_verify_source.py -v
```

The second command's placeholder must be replaced with the exact manifest hash in a separately trusted delivery receipt. A copied hash from an untrusted manifest is not independent authentication. Do not paste the angle-bracket placeholder literally into a shell.

The CLI prints JSON and exits zero on successful source verification, one on a mismatch or filesystem failure. `verify(root, expected_manifest_sha256=None)` provides the same check to Python callers. Neither interface installs, downloads, deploys, invokes another process, rewrites files, repairs a mismatch, nor follows a declared external source path.

## Verify a published Git commit's exact stored bytes

`tools/verify_git_commit.py` is a separate read-only, offline tool. It invokes only the locally installed `git` executable, resolves an exact commit (HEAD or a 40-character SHA-1 ID) and reads its tree and blob objects; it never fetches, checks out, installs, downloads, deploys, commits or pushes. It rejects nonregular Git modes, case conflicts, unsafe paths, missing/unlisted files, altered sizes/hashes, and manifest-pin mismatches. It also confirms each Git blob's object ID, checks Git modes, and reports whether the checkout is clean. Its nine actual local-Git regression tests are in `tools/test_verify_git_commit.py`.

```sh
# After cloning the public repository with no automatic line-ending conversion:
python -B tools/verify_git_commit.py --root . --revision HEAD
python -B -m unittest discover -s tools -p test_verify_git_commit.py -v
# For externally authenticated verification, add this option with the release receipt hash:
# --expected-manifest-sha256 PIN_FROM_RELEASE_RECEIPT
```

The CLI's `filesystem_bytes_verified: false` is deliberate: committed Git objects are not materialized checkout bytes. On Windows, `core.autocrlf` may change line endings, so clone with `git -c core.autocrlf=false clone ...` or pass `-c core.autocrlf=false` to Git during an isolated restore, without changing global settings. Run the separate `verify_source.py` on that clean checkout before installing dependencies. Neither verifier establishes independent review, remote availability, ownership, or permission to redistribute third-party material.

## Manifest and self-reference

`SOURCE_MANIFEST.json` schema 1 contains payload rows with a relative `path`, byte length, lowercase SHA-256 and optional Git mode (`100644` or `100755`). The inventory excludes the manifest itself. Optional payload counts and the SHA-256 of compact sorted path-to-file-hash JSON are checked. The complete count is payload rows plus the manifest. Its own final hash belongs in an external receipt; it cannot straightforwardly contain its own final hash.

Exact paths, case, byte counts, content hashes, duplicate keys and parent/file conflicts are checked. Only portable ASCII source paths are admitted. Traversal, absolute paths, Windows reserved names, symbolic links, junctions and other reparse points are rejected. The real NTFS junction regression failed before the correction and passed afterward. The rejection occurs before scanning the redirected directory.

## Bounds and limitations

The limits are 1 MiB for the manifest, 8 MiB per source file, 16 MiB of declared payload, 2,000 payload files and 4,096 scanned entries. Reads are bounded. A second scan and manifest read detect some changes during verification, but this is **not a sandbox against a malicious concurrent filesystem writer**. Use a quiet isolated directory. Empty directories are not Git source files and have no inventory identity.

Declared executable bits are checked on POSIX. Windows explicitly reports them unsupported; an absent mode declaration is never silently reported verified. A manifest containing only some modes reports partial qualification on POSIX. The recovered 100-file ZIP stored every file as `100644`; the new public manifest retains that source mode.

There are 28 distinct filesystem test definitions. Windows passed 25, skipped the POSIX mode test, and could not create the two symlink fixtures. Linux passed 27, including the actual symlink checks, and skipped the Windows-only junction test. The Windows junction itself was executed, failed before the patch and passed after it. Skipped cases are not Windows or Linux acceptance.

A source check is not a runtime test, secret audit, independent review, license certificate or proof of publication. Reproduction from the local candidate is not a restore from GitHub. After an admitted publication, restore the exact published commit, verify its manifest before installing dependencies, then follow the existing project test instructions. Dependencies may use a disclosed immutable cache; that is not a cold online installation.
