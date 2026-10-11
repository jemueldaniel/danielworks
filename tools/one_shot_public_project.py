#!/usr/bin/env python3
"""One-command, offline assembly and acceptance of original PUBLIC reference code.

Never reads company/private repositories, credentials, env files or networks.
Builds only exporter-approved public profiles and runs a fixed set of sample tests
through the separate verifier, NOT any command from an editable manifest.

This is educational portability evidence, not license clearance, a sandbox,
production deployment or a general-purpose project/code generator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

from export_public_starter import STARTERS, StarterError, export_public_starter
from verify_exported_starter import ProofError, validate, run_profiles


class AssemblyError(Exception):
    def __init__(self, code: str, stage: str):
        self.code = code
        self.stage = stage
        super().__init__(code)


def _fail(code: str, stage: str) -> None:
    raise AssemblyError(code, stage)


def _inside(path: Path, boundary: Path) -> bool:
    return path.resolve(strict=False).is_relative_to(boundary.resolve(strict=False))


def _receipt_preflight(receipt: Path | None, root: Path, output: Path) -> Path | None:
    if receipt is None:
        return None
    if not isinstance(receipt, Path):
        _fail('invalid_receipt_path', 'preflight')
    receipt = receipt.absolute()
    if not receipt.name or receipt.name in {'.', '..'} or receipt.suffix != '.json':
        _fail('invalid_receipt_path', 'preflight')
    parent = receipt.parent
    try:
        if not parent.is_dir() or parent.is_symlink() or not stat.S_ISDIR(parent.stat().st_mode):
            _fail('unsafe_receipt_parent', 'preflight')
        if receipt.exists() or receipt.is_symlink():
            _fail('receipt_already_exists', 'preflight')
        if _inside(receipt, root) or _inside(receipt, output):
            _fail('receipt_inside_protected_tree', 'preflight')
    except (OSError, RuntimeError):
        _fail('unsafe_receipt_path', 'preflight')
    return receipt


def _write_receipt_exclusively(receipt: Path | None, details: dict) -> None:
    if receipt is None:
        return
    blob = (json.dumps(details, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode('utf-8')
    # Explicit exclusive creation; never overwrite another process's receipt.
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    if hasattr(os, 'O_BINARY'):
        flags |= os.O_BINARY
    fd = None
    created = False
    try:
        fd = os.open(receipt, flags, 0o600)
        created = True
        with os.fdopen(fd, 'wb') as f:
            fd = None
            f.write(blob)
            f.flush()
            os.fsync(f.fileno())
        if receipt.read_bytes() != blob:
            _fail('receipt_verification_failed', 'receipt')
    except FileExistsError as exc:
        raise AssemblyError('receipt_already_exists', 'receipt') from exc
    except OSError as exc:
        raise AssemblyError('receipt_write_failed', 'receipt') from exc
    finally:
        if fd is not None:
            os.close(fd)
        # In case of failure after our own creation, avoid partial receipt.
        if created and sys.exc_info()[0] is not None:
            receipt.unlink(missing_ok=True)


def _minimal_runtime_environment() -> dict[str, str]:
    # Do not forward ambient CI tokens, cloud keys, model API credentials or
    # arbitrary PYTHONPATH / NODE_OPTIONS injection into child test programs.
    # These values only allow local public Python/Node tests to run portably.
    keys = ('PATH','HOME','USERPROFILE','TMP','TEMP','TMPDIR','SYSTEMROOT',
            'WINDIR','PATHEXT','LANG','LC_ALL','PYTHONIOENCODING','COMSPEC')
    result = {key: os.environ[key] for key in keys if key in os.environ}
    result['PYTHONDONTWRITEBYTECODE'] = '1'
    result['PYTHONNOUSERSITE'] = '1'
    return result


def assemble(root: Path, source_pin: str, destination: Path, profiles: list[str], *,
             all_executed: bool = False, allow_historical: bool = False,
             run_tests: bool = True, timeout: int = 60, dry_run: bool = False,
             receipt: Path | None = None) -> dict:
    """Return a truthful, machine-readable result without leaking local paths.

    Failed validation/acceptance leaves the exported kit in place for inspection
    but NEVER reports success. The optional receipt is outside source and kit.
    """
    stage = 'preflight'
    try:
        root = Path(root).resolve(strict=True)
        destination = Path(destination).absolute()
        if type(timeout) is not int or not 1 <= timeout <= 120:
            _fail('invalid_timeout', stage)
        receipt = _receipt_preflight(receipt, root, destination)
        if not isinstance(profiles, list) or any(not isinstance(p, str) for p in profiles):
            _fail('invalid_profile_selection', stage)
        selected = list(profiles)
        if all_executed:
            selected.extend(p for p, item in STARTERS.items() if item.qualification == 'executed')
        stage = 'export'
        exported = export_public_starter(root, source_pin, selected, destination,
                                         allow_historical=allow_historical, dry_run=dry_run)
        if dry_run:
            return {'status':'DRY_RUN','stage':'plan','profiles':exported['profiles'],
                    'file_count':exported['selected_files'],'tested_groups':0,
                    'qualification':'not_tested','outputs_created':0}
        pin = exported['output_manifest_sha256']
        stage = 'pretest_integrity'
        verified = validate(destination, pin)
        if verified['source_manifest_sha256'] != source_pin or verified['profiles'] != exported['profiles']:
            _fail('exported_binding_drift', stage)
        groups = []
        if run_tests:
            stage = 'runtime_tests'
            accepted = run_profiles(destination, verified, timeout=timeout,
                                    runtime_env=_minimal_runtime_environment())
            if accepted['tests_run'] != len(exported['profiles']):
                _fail('incomplete_test_execution', stage)
            groups = accepted['groups']
        stage = 'posttest_integrity'
        post = validate(destination, pin)
        if post['profiles'] != verified['profiles'] or post['files'] != verified['files']:
            _fail('posttest_inventory_drift', stage)
        details = {
            'schema': 1,
            'status': 'PASS_TESTED' if run_tests else 'PASS_VERIFIED_ONLY',
            'source': 'original_public_code_only',
            'source_manifest_sha256': source_pin,
            'output_manifest_sha256': pin,
            'file_count': post['files'],
            'profiles': list(exported['profiles']),
            'profile_qualifications': dict(verified['qualifications']),
            'tested_groups': len(groups),
            'groups': [{'profile': g['profile'], 'status': g['status'],
                        'qualification': g['qualification']} for g in groups],
            'posttest_bytes_verified': True,
            'historical_evidence_promoted': False,
            'limits': 'Local educational tests; no license clearance, hosted deployment, isolated untrusted execution or private input.',
        }
        stage = 'receipt'
        _write_receipt_exclusively(receipt, details)
        return details
    except (AssemblyError, StarterError, ProofError, OSError, ValueError, UnicodeError, RuntimeError) as exc:
        code = getattr(exc, 'code', 'invalid_or_unavailable_input')
        return {'status': 'FAIL', 'stage': getattr(exc, 'stage', stage),
                'code': code, 'tested_groups': 0 if stage in ('preflight','export','pretest_integrity') else None,
                'no_production_claim': True}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--expected-source-sha256', required=True)
    ap.add_argument('--destination', required=True, type=Path)
    ap.add_argument('--profile', action='append', default=[])
    ap.add_argument('--all-executed', action='store_true')
    ap.add_argument('--allow-historical', action='store_true')
    ap.add_argument('--no-tests', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--timeout', type=int, default=60)
    ap.add_argument('--receipt', type=Path)
    args = ap.parse_args(argv)
    result = assemble(args.root, args.expected_source_sha256, args.destination,
                      args.profile, all_executed=args.all_executed,
                      allow_historical=args.allow_historical, run_tests=not args.no_tests,
                      timeout=args.timeout, dry_run=args.dry_run, receipt=args.receipt)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result['status'] in ('PASS_TESTED', 'PASS_VERIFIED_ONLY', 'DRY_RUN') else 1


if __name__ == '__main__':
    raise SystemExit(main())
