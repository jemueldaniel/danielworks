#!/usr/bin/env python3
"""Prove exactly what a generated *public* starter contains and actually tests.

This never reads private repositories or shells out through manifest strings.
A manifest SHA-256 supplied outside the exported kit binds its expected bytes.
Runtime groups are local educational examples, not secure process sandboxes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

HEX = re.compile(r'[0-9a-f]{64}\Z')
PATH = re.compile(r'[A-Za-z0-9_./-]+\Z')
MAX_FILES = 120
MAX_ENTRIES = 250
MAX_BYTES = 2_000_000
MAX_MANIFEST = 150_000

# Exact, self-authored public example test commands, never fetched from the
# exported manifest. The bundle may disclose commands but cannot invent them.
TESTS = {
    'agent': ('node', '--test', '--test-reporter=tap', 'examples/mcp_agent/test_runtime.mjs'),
    'jobs': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'examples/durable_jobs', '-v'),
    'training': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'examples/synthetic_training', '-v'),
    'retrieval': ('python', '-B', '-m', 'unittest', '-v', 'test_retrieval.py'),
    'evaluation': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'examples/ranking_eval', '-v'),
    'proof-platform': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'projects/portable-proof-studio', '-v'),
    'event-outbox': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'examples/event_outbox', '-v'),
    'policy': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'examples/tenant_policy', '-v'),
    'ledger': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'examples/atomic_ledger', '-v'),
    'hybrid-search': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'examples/hybrid_search', '-v'),
    'migration': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'examples/migration_guard', '-v'),
    'build-graph': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'examples/build_graph', '-v'),
    'signed-api': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'examples/signed_api', '-v'),
    'interface-lab': ('node', '--test', '--test-reporter=tap', 'examples/interface_lab/test_model.mjs'),
    'ui-atlas': ('node', '--test', '--test-reporter=tap', 'examples/ui_atlas/test_model.mjs'),
    'flow-lab': ('node', '--test', '--test-reporter=tap', 'examples/flow_lab/test_model.mjs'),
    'data-studio': ('node', '--test', '--test-reporter=tap', 'examples/data_studio/test_model.mjs'),
    'proof-gallery': ('node', '--test', '--test-reporter=tap', 'examples/proof_gallery/test_model.mjs'),
    'technology-atlas': ('node', '--test', '--test-reporter=tap', 'examples/technology_atlas/test_model.mjs'),
    'typed-api': ('python', '-B', '-m', 'unittest', 'discover', '-s', 'examples/typed_api_sdk', '-v'),
    'rust-compiler': ('cargo', 'test', '--manifest-path', 'projects/bounded-lang/Cargo.toml', '--locked', '--offline'),
}


class ProofError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str):
    raise ProofError(code)


def _pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            _fail('duplicate_json_key')
        obj[key] = value
    return obj


def _safe_path(p: object) -> str:
    if not isinstance(p, str) or not p or len(p) > 240 or not PATH.fullmatch(p):
        _fail('unsafe_path')
    segments = p.split('/')
    if any(v in ('', '.', '..') or v.endswith('.') for v in segments):
        _fail('unsafe_path')
    if any(v.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL'} for v in segments):
        _fail('unsafe_path')
    return p


def validate(destination: Path, manifest_pin: str) -> dict:
    """Validate against an external expected digest; no execution or writes."""
    root = Path(destination).absolute()
    if not isinstance(manifest_pin, str) or not HEX.fullmatch(manifest_pin):
        _fail('external_pin_required')
    rootstat = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(rootstat.st_mode):
        _fail('invalid_root')
    manifestfile = root / 'REUSE_MANIFEST.json'
    inf = manifestfile.lstat()
    if not stat.S_ISREG(inf.st_mode) or manifestfile.is_symlink() or inf.st_size > MAX_MANIFEST:
        _fail('nonregular_manifest')
    raw = manifestfile.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest_pin:
        _fail('manifest_pin_mismatch')
    try:
        doc = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs)
    except (UnicodeError, ValueError, RecursionError) as e:
        raise ProofError('invalid_manifest') from e
    if not isinstance(doc, dict) or type(doc.get('schema')) is not int or doc['schema'] != 1:
        _fail('invalid_manifest')
    profiles = doc.get('profiles')
    if not isinstance(profiles, list) or not profiles or any(not isinstance(x, str) or x not in TESTS for x in profiles) or len(set(profiles)) != len(profiles):
        _fail('unsupported_profile')
    status = doc.get('profile_qualification')
    if not isinstance(status, dict) or set(status) != set(profiles) or any(status[k] not in ('historical', 'executed') for k in status):
        _fail('invalid_qualification')
    if type(doc.get('tests_executed_by_generator')) is not int or doc['tests_executed_by_generator'] != 0:
        _fail('false_test_claim')
    if not isinstance(doc.get('externally_pinned_source_manifest_sha256'), str) or not HEX.fullmatch(doc['externally_pinned_source_manifest_sha256']):
        _fail('unbound_source')
    rows = doc.get('files')
    if not isinstance(rows, list) or not rows or len(rows) > MAX_FILES:
        _fail('invalid_manifest')
    expected = {}
    allkeys = set()
    total = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'path', 'bytes', 'sha256', 'mode'}:
            _fail('invalid_manifest_row')
        p = _safe_path(row.get('path'))
        key = p.casefold()
        if key in allkeys or p in ('README.md', 'REUSE_MANIFEST.json'):
            _fail('duplicate_path')
        allkeys.add(key)
        b = row.get('bytes')
        sha = row.get('sha256')
        if type(b) is not int or b < 0 or b > MAX_BYTES or row.get('mode') != '100644' or not isinstance(sha, str) or not HEX.fullmatch(sha):
            _fail('invalid_manifest_row')
        total += b
        if total > MAX_BYTES:
            _fail('resource_limit')
        expected[p] = (sha, b)
    readme_pin = doc.get('generated_readme_sha256')
    if not isinstance(readme_pin, str) or not HEX.fullmatch(readme_pin):
        _fail('invalid_readme_pin')
    expected['README.md'] = (readme_pin, None)
    actual_files = {}
    dirnames = set()
    count = 0
    pending = [root]
    while pending:
        directory = pending.pop()
        for child in directory.iterdir():
            count += 1
            if count > MAX_ENTRIES:
                _fail('resource_limit')
            name = _safe_path(child.relative_to(root).as_posix())
            info = child.lstat()
            if child.is_symlink() or bool(getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)):
                _fail('unsafe_link')
            key = name.casefold()
            if stat.S_ISDIR(info.st_mode):
                if key in dirnames or key in actual_files:
                    _fail('case_collision')
                dirnames.add(key)
                pending.append(child)
            elif stat.S_ISREG(info.st_mode):
                if key in actual_files or key in dirnames:
                    _fail('case_collision')
                actual_files[key] = name
                if name == 'REUSE_MANIFEST.json':
                    continue
                wanted = expected.get(name)
                if wanted is None or (wanted[1] is not None and wanted[1] != info.st_size):
                    _fail('extra_or_changed_file')
                if hashlib.sha256(child.read_bytes()).hexdigest() != wanted[0]:
                    _fail('content_hash_mismatch')
            else:
                _fail('nonregular_entry')
    if set(actual_files) != {n.casefold() for n in expected} | {'reuse_manifest.json'}:
        _fail('missing_file')
    return {'status': 'PASS', 'manifest_sha256': manifest_pin, 'source_manifest_sha256': doc['externally_pinned_source_manifest_sha256'],
            'files': len(actual_files), 'profiles': profiles, 'qualifications': status, 'tests_run': 0,
            'scope': 'exact local public-kit byte verification; not ownership, license or runtime proof'}


def run_profiles(destination: Path, verified: dict, timeout: int = 60, *, runtime_env: dict[str, str] | None = None) -> dict:
    """Run fixed public tests; optionally receive an explicitly restricted environment."""
    if type(timeout) is not int or not 1 <= timeout <= 120:
        _fail('invalid_timeout')
    root = Path(destination).absolute()
    groups = []
    for profile in verified['profiles']:
        args = list(TESTS[profile])
        if args[0] == 'python':
            args[0] = sys.executable
        else:
            executable = shutil.which(args[0])
            if not executable:
                _fail('runtime_unavailable')
            args[0] = executable
        cwd = root / ('examples/retrieval_lab' if profile == 'retrieval' else '.')
        try:
            proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                                  timeout=timeout, check=False, env={**(os.environ if runtime_env is None else runtime_env), 'PYTHONDONTWRITEBYTECODE':'1'})
        except subprocess.TimeoutExpired as e:
            raise ProofError('timeout') from e
        if proc.returncode != 0:
            _fail('test_failed')
        output = proc.stdout + '\n' + proc.stderr
        if profile in ('agent', 'interface-lab', 'ui-atlas', 'flow-lab', 'data-studio', 'proof-gallery', 'technology-atlas'):
            has_tests = (re.search(r'^# tests [1-9]\d*$', output, re.M)
                         and re.search(r'^# pass [1-9]\d*$', output, re.M)
                         and re.search(r'^# fail 0$', output, re.M))
        elif profile == 'rust-compiler':
            has_tests = re.search(r'test result: ok\. [1-9]\d* passed', output)
        else:
            has_tests = re.search(r'^Ran [1-9]\d* tests? in ', output, re.M)
        if not has_tests:
            _fail('no_tests_executed')
        groups.append({'profile': profile, 'status': 'PASS', 'qualification': verified['qualifications'][profile]})
    return {'status': 'PASS', 'tests_run': len(groups), 'groups': groups,
            'qualification_boundary': 'Tests passed on this machine only; historical labels are retained'}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--expected-manifest-sha256', required=True)
    p.add_argument('--run-tests', action='store_true')
    args = p.parse_args(argv)
    try:
        report = validate(args.destination, args.expected_manifest_sha256)
        if args.run_tests:
            report.update(run_profiles(args.destination, report))
    except (ProofError, OSError, ValueError) as e:
        report = {'status': 'FAIL', 'code': getattr(e,'code','invalid_input')}
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
