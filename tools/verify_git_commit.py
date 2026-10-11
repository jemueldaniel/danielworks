#!/usr/bin/env python3
"""Read-only verification of a local Git commit's exact blob bytes and manifest.

Runs Git locally with fixed argv and no network, worktree changes or commits.
Checks committed objects, not checkout line endings. Run verify_source.py to
separately qualify the exact materialized filesystem files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from verify_source import _portable, _pairs, VerificationError

MAX_FILES = 2000
MAX_FILE_BYTES = 8_388_608
MAX_TOTAL_BYTES = 16_777_216
MAX_MANIFEST_BYTES = 1_048_576
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')


class GitVerificationError(Exception):
    """Safe failure code, independent of local filesystem location."""


def reject(reason: str):
    raise GitVerificationError(reason)


def _git(root: Path, *args: str) -> bytes:
    try:
        # Avoid optional index writes and local fsmonitor hooks during status.
        result = subprocess.run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                                 '-c', 'core.untrackedCache=false', '-C', str(root), *args],
                                capture_output=True, check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        reject('git_unavailable')
    if result.returncode != 0:
        reject('git_unavailable')
    return result.stdout


def _blob(root: Path, oid: str, limit: int) -> bytes:
    if not HEX40.fullmatch(oid):
        reject('invalid_git_tree')
    raw_size = _git(root, 'cat-file', '-s', oid).strip()
    try:
        n = int(raw_size)
    except ValueError:
        reject('invalid_git_object')
    if n < 0 or n > limit:
        reject('resource_limit')
    body = _git(root, 'cat-file', 'blob', oid)
    if len(body) != n:
        reject('invalid_git_object')
    actual = hashlib.sha1(b'blob ' + str(len(body)).encode('ascii') + b'\x00' + body).hexdigest()
    if actual != oid:
        reject('invalid_git_object')
    return body


def verify(root: Path, *, revision: str = 'HEAD',
           expected_manifest_sha256: str | None = None) -> dict:
    root = Path(root).absolute()
    if not root.is_dir() or root.is_symlink():
        reject('invalid_root')
    if revision != 'HEAD' and (not isinstance(revision, str) or not HEX40.fullmatch(revision)):
        reject('invalid_revision')
    if expected_manifest_sha256 is not None and (
        not isinstance(expected_manifest_sha256, str)
        or not HEX64.fullmatch(expected_manifest_sha256)
    ):
        reject('invalid_expected_hash')
    # Refuse subdirectories and other repositories with misleading -C parents.
    actual_root = _git(root, 'rev-parse', '--show-toplevel').decode('utf-8', 'strict').strip()
    if Path(actual_root).resolve() != root.resolve():
        reject('invalid_root')
    commit = _git(root, 'rev-parse', '--verify', revision + '^{commit}').decode('ascii').strip()
    if not HEX40.fullmatch(commit):
        reject('invalid_revision')
    tree_oid = _git(root, 'rev-parse', commit + '^{tree}').decode('ascii').strip()
    tree_raw = _git(root, 'ls-tree', '-r', '-z', commit)
    rows = [record for record in tree_raw.split(b'\x00') if record]
    if not rows or len(rows) > MAX_FILES or len(tree_raw) > 1_048_576:
        reject('resource_limit')
    tree: dict[str, tuple[str, str]] = {}
    names: set[str] = set()
    for item in rows:
        try:
            descriptor, path_raw = item.split(b'\t', 1)
            mode, kind, oid = descriptor.decode('ascii').split(' ')
            name = _portable(path_raw.decode('utf-8', 'strict'))
        except (ValueError, UnicodeError, VerificationError):
            reject('invalid_git_tree')
        if kind != 'blob' or mode not in ('100644', '100755'):
            reject('nonregular_git_entry')
        if not HEX40.fullmatch(oid) or name.casefold() in names:
            reject('invalid_git_tree')
        names.add(name.casefold())
        tree[name] = (mode, oid)
    if 'SOURCE_MANIFEST.json' not in tree:
        reject('missing_manifest')
    manifest_raw = _blob(root, tree['SOURCE_MANIFEST.json'][1], MAX_MANIFEST_BYTES)
    manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
    if expected_manifest_sha256 is not None and expected_manifest_sha256 != manifest_sha:
        reject('manifest_hash_mismatch')
    try:
        manifest = json.loads(manifest_raw.decode('utf-8'), object_pairs_hook=_pairs)
    except (ValueError, UnicodeError, RecursionError, VerificationError):
        reject('invalid_manifest')
    if not isinstance(manifest, dict) or type(manifest.get('schema')) is not int or manifest['schema'] != 1:
        reject('invalid_manifest')
    entries = manifest.get('files')
    if not isinstance(entries, list) or not entries or len(entries) > MAX_FILES:
        reject('invalid_manifest')
    expected: dict[str, dict] = {}
    casefolded: set[str] = set()
    total = 0
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) - {'path', 'sha256', 'bytes', 'mode'}:
            reject('invalid_manifest')
        try:
            name = _portable(entry.get('path'))
        except VerificationError:
            reject('invalid_manifest')
        if name.casefold() == 'source_manifest.json' or name.casefold() in casefolded:
            reject('invalid_manifest')
        casefolded.add(name.casefold())
        count, digest, mode = entry.get('bytes'), entry.get('sha256'), entry.get('mode')
        if (type(count) is not int or count < 0 or count > MAX_FILE_BYTES
                or not isinstance(digest, str) or not HEX64.fullmatch(digest)
                or mode not in ('100644', '100755')):
            reject('invalid_manifest')
        total += count
        if total > MAX_TOTAL_BYTES:
            reject('resource_limit')
        expected[name] = entry
    if set(tree) != set(expected) | {'SOURCE_MANIFEST.json'}:
        reject('inventory_mismatch')
    binding = hashlib.sha256(json.dumps({k: v['sha256'] for k, v in expected.items()},
                                         sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    metadata = {
        'inventory_file_count': len(expected),
        'complete_checkpoint_file_count_including_this_manifest': len(expected) + 1,
        'payload_bytes_excluding_this_manifest': total,
        'payload_path_sha256_binding': binding,
    }
    for key, value in metadata.items():
        if key in manifest and (type(manifest[key]) is not type(value) or manifest[key] != value):
            reject('manifest_metadata_mismatch')
    for name, entry in expected.items():
        mode, oid = tree[name]
        if mode != entry['mode']:
            reject('file_mode_mismatch')
        data = _blob(root, oid, MAX_FILE_BYTES)
        if len(data) != entry['bytes']:
            reject('file_size_mismatch')
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            reject('file_hash_mismatch')
    working_tree_clean = _git(root, 'status', '--porcelain=v1', '--untracked-files=normal').strip() == b''
    return {
        'status': 'PASS', 'commit': commit, 'tree': tree_oid,
        'tree_files': len(tree), 'manifest_sha256': manifest_sha,
        'manifest_authentication': 'external_hash_matched' if expected_manifest_sha256 else 'observed_only',
        'working_tree_clean': working_tree_clean,
        'filesystem_bytes_verified': False,
        'scope': 'local committed Git objects only; checkout bytes require tools/verify_source.py',
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--revision', default='HEAD')
    p.add_argument('--expected-manifest-sha256')
    args = p.parse_args()
    try:
        result = verify(args.root, revision=args.revision,
                        expected_manifest_sha256=args.expected_manifest_sha256)
    except GitVerificationError as error:
        result = {'status': 'FAIL', 'code': str(error)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
