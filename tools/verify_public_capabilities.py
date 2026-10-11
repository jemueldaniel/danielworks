#!/usr/bin/env python3
"""Validate a public-only skill-to-source map against a pinned source manifest.

This is a structural check only: existing tests must be *executed separately*.
No file is modified, no network/subprocess started, and no private source read.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from verify_source import VerificationError, _pairs, _portable, verify

MAX_INDEX_BYTES = 65536
REQUIRED_FIELDS = {'id', 'discipline', 'qualification', 'implementation', 'tests', 'boundary'}
QUALIFICATIONS = {'executed', 'historical', 'source_only', 'not_verified'}


class ClaimError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise ClaimError(code)


def validate_index(data: object, inventory: set[str]) -> dict:
    if not isinstance(data, dict) or set(data) != {'schema', 'purpose', 'claims'} or type(data['schema']) is not int or data['schema'] != 1:
        _fail('invalid_index_schema')
    purpose = data['purpose']
    if not isinstance(purpose, str) or not 20 <= len(purpose) <= 400 or any(ord(c) < 32 for c in purpose):
        _fail('invalid_disclosure')
    claims = data['claims']
    if re.search(r'(?i)(?:[\w.+-]+@[\w.-]+|https?://|[a-z]:[\\/])', purpose):
        _fail('external_or_sensitive_reference')
    if not isinstance(claims, list) or not 1 <= len(claims) <= 100:
        _fail('invalid_claim_count')
    ids: set[str] = set()
    referenced: set[str] = set()
    counts = {k: 0 for k in sorted(QUALIFICATIONS)}
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != REQUIRED_FIELDS:
            _fail('invalid_claim_schema')
        id = claim['id']
        if not isinstance(id, str) or not re.fullmatch(r'[a-z][a-z0-9-]{2,47}', id) or id in ids:
            _fail('invalid_or_duplicate_id')
        ids.add(id)
        for field in ('discipline', 'boundary'):
            t = claim[field]
            if not isinstance(t, str) or not 12 <= len(t) <= 250 or any(ord(c) < 32 for c in t):
                _fail('invalid_claim_description')
            # Public-only: disallow embedded email addresses, URLs, machine-local paths or tokens.
            if re.search(r'(?i)(?:[\w.+-]+@[\w.-]+|https?://|[a-z]:[\\/]|(?:sk|ghp|github_pat)_[A-Za-z0-9]{12,})', t):
                _fail('external_or_sensitive_reference')
        q = claim['qualification']
        if not isinstance(q, str) or q not in QUALIFICATIONS:
            _fail('invalid_qualification')
        counts[q] += 1
        paths: set[str] = set()
        for field in ('implementation', 'tests'):
            entries = claim[field]
            if not isinstance(entries, list) or len(entries) > 8:
                _fail('invalid_reference_list')
            for value in entries:
                try:
                    p = _portable(value)
                except VerificationError:
                    _fail('invalid_public_path')
                if p in paths:
                    _fail('duplicate_claim_path')
                if p not in inventory or any(seg in {'.git', '.env', 'node_modules', 'private', 'secrets'} for seg in p.lower().split('/')):
                    _fail('unpublished_or_excluded_path')
                paths.add(p)
                referenced.add(p)
        if q == 'not_verified' and (paths or claim['implementation'] or claim['tests']):
            _fail('unverified_claim_has_public_proof')
        if q != 'not_verified' and not claim['implementation']:
            _fail('missing_implementation')
        if q in {'executed', 'historical'} and not claim['tests']:
            _fail('missing_test_entrypoints')
    return {'status': 'PASS', 'scope': 'public_reference_and_current_file_hashes_only',
            'claims': len(claims), 'qualifications': counts, 'unique_public_file_references': len(referenced),
            'runtime_tests_executed_by_this_command': 0}


def verify_capabilities(root: Path, expected_manifest_sha256: str | None = None) -> dict:
    report = verify(root, expected_manifest_sha256)
    p = root / 'docs' / 'PUBLIC_CAPABILITIES.json'
    try:
        if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_INDEX_BYTES:
            _fail('missing_or_oversize_index')
        raw = p.read_bytes()
        index = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs)
        manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text('utf-8'), object_pairs_hook=_pairs)
    except (ValueError, UnicodeError, OSError, RecursionError, VerificationError):
        _fail('invalid_index_json')
    return {**validate_index(index, {f['path'] for f in manifest['files']}),
            'manifest_sha256': report['manifest_sha256'],
            'manifest_authentication': report['manifest_authentication']}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--expected-manifest-sha256')
    args = parser.parse_args()
    try:
        out = verify_capabilities(args.root, args.expected_manifest_sha256)
    except (ClaimError, VerificationError, OSError, ValueError) as e:
        out = {'status': 'FAIL', 'code': getattr(e, 'code', 'invalid_input')}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
