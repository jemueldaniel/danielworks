#!/usr/bin/env python3
"""Verify a quiet, source-only checkout. No writes, installs, subprocesses or network.

The manifest excludes itself: supply its expected hash out-of-band to authenticate
it. Without that hash, this proves internal byte consistency, not authorship or
trust. Only normal top-level .git metadata is excluded. Run before installing or
building. This is not a sandbox against a malicious concurrent filesystem writer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_MANIFEST_BYTES = 1_048_576
MAX_FILE_BYTES = 8_388_608
MAX_PAYLOAD_BYTES = 16_777_216
MAX_FILES = 2000
MAX_ENTRIES = 4096
MANIFEST = 'SOURCE_MANIFEST.json'
HEX = re.compile(r'[0-9a-f]{64}\Z')
RESERVED = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{n}' for p in ('COM', 'LPT') for n in range(1, 10)}

class VerificationError(Exception):
    """Stable machine-readable failure, without file contents or absolute paths."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise VerificationError(code)


def _portable(name: object) -> str:
    if not isinstance(name, str) or not name or len(name) > 240 or not re.fullmatch(r'[A-Za-z0-9_./-]+', name):
        _fail('unsafe_path')
    parts = name.split('/')
    if any(p in ('', '.', '..') or p.endswith('.') or p.split('.')[0].upper() in RESERVED for p in parts):
        _fail('unsafe_path')
    if parts[0].casefold() == '.git':
        _fail('unsafe_path')
    return name


def _is_reparse(info: os.stat_result) -> bool:
    # Windows junctions are directory reparse points, not POSIX symlinks.
    return bool(getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))


def _read_regular(path: Path, limit: int) -> bytes:
    info = path.lstat()
    if _is_reparse(info) or not stat.S_ISREG(info.st_mode):
        _fail('nonregular_file')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        before = os.fstat(stream.fileno())
        if _is_reparse(before) or not stat.S_ISREG(before.st_mode):
            _fail('nonregular_file')
        if before.st_size > limit:
            _fail('resource_limit')
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_mode)
    if identity(before) != identity(after) or identity(after) != identity(current):
        _fail('source_changed')
    if len(data) > limit:
        _fail('resource_limit')
    return data


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _fail('duplicate_json_key')
        result[key] = value
    return result


def _scan(root: Path) -> tuple[set[str], list[str]]:
    pending = [root]
    files: set[str] = set()
    names: set[str] = set()
    excluded: list[str] = []
    count = 0
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                count += 1
                if count > MAX_ENTRIES:
                    _fail('resource_limit')
                relative = (directory / entry.name).relative_to(root).as_posix()
                info = entry.stat(follow_symlinks=False)
                if _is_reparse(info) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                    _fail('nonregular_file')
                if relative == '.git':
                    excluded.append(relative)
                    continue
                _portable(relative)
                folded = relative.casefold()
                if folded in names:
                    _fail('path_collision')
                names.add(folded)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(directory / entry.name)
                else:
                    files.add(relative)
    return files, excluded


def verify(root: Path, expected_manifest_sha256: str | None = None) -> dict:
    """Return a successful verification report or raise VerificationError.

    Caller must provide a quiet isolated tree. Executable-bit qualification is
    POSIX-only; declared modes are explicitly unverified on Windows.
    """
    root = Path(root).absolute()
    if _is_reparse(root.lstat()) or root.is_symlink() or not root.is_dir():
        _fail('invalid_root')
    raw = _read_regular(root / MANIFEST, MAX_MANIFEST_BYTES)
    manifest_hash = hashlib.sha256(raw).hexdigest()
    if expected_manifest_sha256 is not None:
        if not isinstance(expected_manifest_sha256, str) or not HEX.fullmatch(expected_manifest_sha256):
            _fail('invalid_expected_hash')
        if expected_manifest_sha256 != manifest_hash:
            _fail('manifest_hash_mismatch')
    try:
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs)
    except (ValueError, UnicodeError, RecursionError):
        _fail('invalid_manifest')
    if not isinstance(data, dict) or type(data.get('schema')) is not int or data['schema'] != 1:
        _fail('invalid_manifest')
    rows = data.get('files')
    if not isinstance(rows, list) or not rows or len(rows) > MAX_FILES:
        _fail('invalid_manifest')
    expected: dict[str, dict] = {}
    folded: set[str] = set()
    total = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) - {'path', 'bytes', 'sha256', 'mode'}:
            _fail('invalid_manifest')
        name = _portable(row.get('path'))
        if name.casefold() == MANIFEST.casefold():
            _fail('self_manifest_entry')
        if name.casefold() in folded:
            _fail('path_collision')
        folded.add(name.casefold())
        size, digest = row.get('bytes'), row.get('sha256')
        if type(size) is not int or size < 0 or not isinstance(digest, str) or not HEX.fullmatch(digest):
            _fail('invalid_manifest')
        if 'mode' in row and row['mode'] not in ('100644', '100755'):
            _fail('invalid_manifest')
        total += size
        if size > MAX_FILE_BYTES or total > MAX_PAYLOAD_BYTES:
            _fail('resource_limit')
        expected[name] = row
    for name in expected:
        parent = name.rpartition('/')[0]
        while parent:
            if parent.casefold() in folded:
                _fail('path_collision')
            parent = parent.rpartition('/')[0]
    binding = hashlib.sha256(json.dumps({n: r['sha256'] for n, r in expected.items()}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    metadata = {'inventory_file_count': len(rows), 'complete_checkpoint_file_count_including_this_manifest': len(rows) + 1,
                'payload_bytes_excluding_this_manifest': total, 'payload_path_sha256_binding': binding}
    for key, value in metadata.items():
        if key in data and (type(data[key]) is not type(value) or data[key] != value):
            _fail('manifest_metadata_mismatch')
    actual, excluded = _scan(root)
    if actual != set(expected) | {MANIFEST}:
        _fail('inventory_mismatch')
    declared_modes = 0
    for name, row in expected.items():
        content = _read_regular(root / name, MAX_FILE_BYTES)
        if len(content) != row['bytes']:
            _fail('file_size_mismatch')
        if hashlib.sha256(content).hexdigest() != row['sha256']:
            _fail('file_hash_mismatch')
        if 'mode' in row:
            declared_modes += 1
            if os.name != 'nt':
                mode = '100755' if (root / name).lstat().st_mode & 0o111 else '100644'
                if mode != row['mode']:
                    _fail('file_mode_mismatch')
    if _scan(root) != (actual, excluded) or _read_regular(root / MANIFEST, MAX_MANIFEST_BYTES) != raw:
        _fail('source_changed')
    return {'status': 'PASS', 'payload_files': len(expected), 'total_files_including_manifest': len(expected) + 1,
            'payload_bytes': total, 'payload_path_sha256_binding': binding, 'manifest_sha256': manifest_hash,
            'manifest_authentication': 'external_hash_matched' if expected_manifest_sha256 is not None else 'observed_only',
            'mode_verification': ('not_supported_on_windows' if os.name == 'nt' else ('verified' if declared_modes == len(expected) else 'partially_verified')) if declared_modes else 'not_declared',
            'mode_entries_declared': declared_modes, 'mode_entries_checked': 0 if os.name == 'nt' else declared_modes,
            'excluded_metadata': excluded, 'scope': 'quiet source-only tree; not runtime, review, provenance or remote-publication qualification'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--expected-manifest-sha256')
    args = parser.parse_args()
    try:
        report = verify(args.root, args.expected_manifest_sha256)
    except (VerificationError, OSError) as error:
        report = {'status': 'FAIL', 'code': error.code if isinstance(error, VerificationError) else 'filesystem_error'}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
