#!/usr/bin/env python3
"""Repeat tests of an externally pinned PUBLIC kit without erasing failures.

No private sources, secrets, arbitrary manifest commands, shell interpolation,
network installs, production claims, or test retries that hide negative evidence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Callable

from one_shot_public_project import _minimal_runtime_environment
from verify_exported_starter import ProofError, run_profiles, validate

_HEX = re.compile(r"[0-9a-f]{64}\Z")
_CODE = re.compile(r"[a-z][a-z0-9_]{1,63}\Z")


def _error(code: str) -> dict:
    return {"schema": 1, "status": "FAIL", "stage": "preflight", "code": code,
            "tests_passed": 0, "no_production_claim": True}


def _receipt_preflight(destination: Path, receipt: Path | None) -> Path | None:
    if receipt is None:
        return None
    if not isinstance(receipt, Path) or receipt.suffix != ".json":
        raise ValueError("invalid_receipt")
    candidate = receipt.absolute()
    parent = candidate.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError("unsafe_receipt_parent")
    if candidate.exists() or candidate.is_symlink():
        raise ValueError("receipt_exists")
    source = Path(__file__).resolve().parents[1]
    if candidate.resolve(strict=False).is_relative_to(destination.resolve(strict=False)) or candidate.resolve(strict=False).is_relative_to(source):
        raise ValueError("receipt_inside_protected_tree")
    return candidate


def _write_once(path: Path | None, report: dict) -> None:
    if path is None:
        return
    raw = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = None
    created = False
    try:
        fd = os.open(path, flags, 0o600)
        created = True
        with os.fdopen(fd, "wb") as stream:
            fd = None
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != raw:
            raise OSError("receipt_readback_failure")
    except Exception:
        if created:
            path.unlink(missing_ok=True)
        raise
    finally:
        if fd is not None:
            os.close(fd)


def diagnose(destination: Path, expected_manifest_sha256: str, *, rounds: int = 2,
             timeout: int = 60, receipt: Path | None = None,
             selected_profiles: list[str] | None = None,
             runner: Callable | None = None) -> dict:
    """Report every pass/fail and preserve every failure over all requested rounds.

    A test's failure is retained if later diagnostics pass. A source-integrity
    failure ends the run immediately. All test commands are owned by the
    existing public allowlisted runner, not by editable manifest strings.
    """
    if type(rounds) is not int or not 1 <= rounds <= 3:
        return _error("invalid_rounds")
    if type(timeout) is not int or not 1 <= timeout <= 120:
        return _error("invalid_timeout")
    if type(expected_manifest_sha256) is not str or not _HEX.fullmatch(expected_manifest_sha256):
        return _error("invalid_source_pin")
    try:
        root = Path(destination).absolute()
        if root.is_symlink() or not root.is_dir():
            return _error("invalid_destination")
        target = _receipt_preflight(root, receipt)
        verified = validate(root, expected_manifest_sha256)
        original = (verified["manifest_sha256"], verified["files"], tuple(verified["profiles"]), dict(verified["qualifications"]))
        profiles = list(verified["profiles"])
        if selected_profiles is not None:
            if type(selected_profiles) is not list or not selected_profiles or any(type(p) is not str or p not in profiles for p in selected_profiles) or len(set(selected_profiles)) != len(selected_profiles):
                return _error("invalid_selected_profile")
            profiles = [p for p in profiles if p in selected_profiles]
    except ProofError as ex:
        return _error(ex.code if _CODE.fullmatch(str(ex.code)) else "invalid_public_kit")
    except (OSError, TypeError, ValueError, KeyError):
        return _error("invalid_public_kit_or_receipt")

    runner = run_profiles if runner is None else runner
    steps: list[dict] = []
    failed = 0
    passed = 0
    integrity_failed = False
    for round_number in range(1, rounds + 1):
        for profile in profiles:
            entry = {"round": round_number, "profile": profile, "qualification": verified["qualifications"][profile]}
            try:
                before = validate(root, expected_manifest_sha256)
                if (before["manifest_sha256"], before["files"], tuple(before["profiles"]), dict(before["qualifications"])) != original:
                    raise ProofError("source_changed")
                sub = {**verified, "profiles": [profile]}
                outcome = runner(root, sub, timeout=timeout,
                                 runtime_env=_minimal_runtime_environment())
                if outcome.get("status") != "PASS" or outcome.get("tests_run") != 1 or len(outcome.get("groups", [])) != 1 or outcome["groups"][0].get("profile") != profile or outcome["groups"][0].get("status") != "PASS":
                    raise ProofError("incomplete_test_execution")
                entry["status"] = "PASS"
                passed += 1
            except ProofError as ex:
                entry["status"] = "FAIL"
                entry["code"] = ex.code if isinstance(ex.code, str) and _CODE.fullmatch(ex.code) else "test_failed"
                failed += 1
            except (OSError, RuntimeError, ValueError, TypeError, KeyError):
                entry["status"] = "FAIL"
                entry["code"] = "runtime_unavailable"
                failed += 1
            steps.append(entry)
            try:
                after = validate(root, expected_manifest_sha256)
                if (after["manifest_sha256"], after["files"], tuple(after["profiles"]), dict(after["qualifications"])) != original:
                    raise ProofError("source_changed")
            except (ProofError, OSError, TypeError, ValueError, KeyError):
                integrity_failed = True
                steps.append({"round": round_number, "profile": profile, "status": "FAIL",
                              "code": "posttest_integrity_failure"})
                failed += 1
                break
        if integrity_failed:
            break
    report = {"schema": 1, "status": "PASS_REPEATED" if failed == 0 else "FAIL_RECORDED",
              "source": "externally_pinned_original_public_kit_only",
              "source_manifest_sha256": verified["source_manifest_sha256"],
              "export_manifest_sha256": expected_manifest_sha256,
              "profiles_selected": profiles, "rounds_requested": rounds,
              "tests_passed": passed, "failures": failed, "groups": steps,
              "posttest_bytes_verified": not integrity_failed,
              "historical_evidence_promoted": False,
              "no_production_claim": True}
    try:
        _write_once(target, report)
    except OSError:
        return {"schema": 1, "status": "FAIL", "stage": "receipt", "code": "receipt_write_failed",
                "tests_passed": passed, "failures": failed,
                "no_production_claim": True}
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--profile", action="append", default=[])
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    report = diagnose(args.destination, args.expected_manifest_sha256,
                      rounds=args.rounds, timeout=args.timeout, receipt=args.receipt,
                      selected_profiles=args.profile or None)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["status"] == "PASS_REPEATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
