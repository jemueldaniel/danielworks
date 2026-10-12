#!/usr/bin/env python3
"""Offline, non-overwriting transfer of *public-only* tested demonstration slices.

A job's private source, APIs, credentials, and business logic are not inputs.
The trusted outer receipt pins SOURCE_MANIFEST.json; the manifest pins every
public source byte. Claim statuses are disclosures, NOT test execution.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

from verify_public_capabilities import verify_capabilities, ClaimError
from verify_source import VerificationError

MAX_OUTPUT_BYTES = 2_000_000
_ID = re.compile(r"[a-z][a-z0-9-]{2,39}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")

@dataclass(frozen=True)
class Starter:
    claim: str
    paths: tuple[str, ...]
    test_command: str
    qualification: str


# These are intentional, ORIGINAL PUBLIC demonstrations from the already
# published source tree. No private repository, account, or local path appears.
STARTERS: dict[str, Starter] = {
    "agent": Starter("agent-recovery", (
        "examples/mcp_agent/README.md",
        "examples/mcp_agent/runtime.mjs",
        "examples/mcp_agent/test_runtime.mjs",
    ), "node --test --test-reporter=tap examples/mcp_agent/test_runtime.mjs", "executed"),
    "jobs": Starter("durable-jobs", (
        "examples/durable_jobs/README.md",
        "examples/durable_jobs/jobs.py",
        "examples/durable_jobs/demo.py",
        "examples/durable_jobs/test_jobs.py",
    ), "python -B -m unittest discover -s examples/durable_jobs -v", "executed"),
    "training": Starter("cpu-model-training", (
        "examples/synthetic_training/README.md",
        "examples/synthetic_training/training.py",
        "examples/synthetic_training/demo.py",
        "examples/synthetic_training/test_training.py",
    ), "python -B -m unittest discover -s examples/synthetic_training -v", "executed"),
    "retrieval": Starter("retrieval-and-grading", (
        "examples/retrieval_lab/README.md",
        "examples/retrieval_lab/retrieval.py",
        "examples/retrieval_lab/dataset.v1.json",
        "examples/retrieval_lab/test_retrieval.py",
    ), "(cd examples/retrieval_lab && python -B -m unittest -v test_retrieval.py)", "executed"),
    "evaluation": Starter("retrieval-and-grading", (
        "examples/ranking_eval/README.md",
        "examples/ranking_eval/evaluation.py",
        "examples/ranking_eval/synthetic.json",
        "examples/ranking_eval/test_evaluation.py",
    ), "python -B -m unittest discover -s examples/ranking_eval -v", "executed"),
    "proof-platform": Starter("portable-proof-platform", (
        "projects/portable-proof-studio/README.md",
        "projects/portable-proof-studio/store.py",
        "projects/portable-proof-studio/server.py",
        "projects/portable-proof-studio/web/index.html",
        "projects/portable-proof-studio/web/style.css",
        "projects/portable-proof-studio/web/app.js",
        "projects/portable-proof-studio/test_store.py",
        "projects/portable-proof-studio/test_http.py",
        "projects/portable-proof-studio/test_web.py",
    ), "python -B -m unittest discover -s projects/portable-proof-studio -v", "executed"),
    "event-outbox": Starter("signed-event-delivery", (
        "examples/event_outbox/README.md",
        "examples/event_outbox/event_outbox.py",
        "examples/event_outbox/http_gateway.py",
        "examples/event_outbox/demo.py",
        "examples/event_outbox/test_event_outbox.py",
    ), "python -B -m unittest discover -s examples/event_outbox -v", "executed"),
    "policy": Starter("tenant-policy-audit", (
        "examples/tenant_policy/README.md",
        "examples/tenant_policy/policy.py",
        "examples/tenant_policy/demo.py",
        "examples/tenant_policy/test_policy.py",
    ), "python -B -m unittest discover -s examples/tenant_policy -v", "executed"),
    "ledger": Starter("sqlite-double-entry-ledger", (
        "examples/atomic_ledger/README.md",
        "examples/atomic_ledger/ledger.py",
        "examples/atomic_ledger/demo.py",
        "examples/atomic_ledger/test_ledger.py",
    ), "python -B -m unittest discover -s examples/atomic_ledger -v", "executed"),
    "hybrid-search": Starter("hybrid-retrieval-evaluation", (
        "examples/hybrid_search/README.md",
        "examples/hybrid_search/hybrid.py",
        "examples/hybrid_search/demo.py",
        "examples/hybrid_search/test_hybrid.py",
    ), "python -B -m unittest discover -s examples/hybrid_search -v", "executed"),
    "migration": Starter("sqlite-migration-gate", (
        "examples/migration_guard/README.md",
        "examples/migration_guard/migration.py",
        "examples/migration_guard/demo.py",
        "examples/migration_guard/test_migration.py",
    ), "python -B -m unittest discover -s examples/migration_guard -v", "executed"),
    "build-graph": Starter("bounded-workflow-dag", (
        "examples/build_graph/README.md",
        "examples/build_graph/graph.py",
        "examples/build_graph/demo.py",
        "examples/build_graph/test_graph.py",
    ), "python -B -m unittest discover -s examples/build_graph -v", "executed"),
    "signed-api": Starter("signed-request-replay-guard", (
        "examples/signed_api/README.md",
        "examples/signed_api/signed_api.py",
        "examples/signed_api/demo.py",
        "examples/signed_api/test_signed_api.py",
    ), "python -B -m unittest discover -s examples/signed_api -v", "executed"),
    "interface-lab": Starter("public-interface-laboratory", (
        "examples/interface_lab/README.md",
        "examples/interface_lab/index.html",
        "examples/interface_lab/style.css",
        "examples/interface_lab/model.mjs",
        "examples/interface_lab/app.mjs",
        "examples/interface_lab/test_model.mjs",
    ), "node --test --test-reporter=tap examples/interface_lab/test_model.mjs", "executed"),
    "flow-lab": Starter("interactive-flow-graph-ui", (
        "examples/flow_lab/README.md",
        "examples/flow_lab/index.html",
        "examples/flow_lab/styles.css",
        "examples/flow_lab/model.mjs",
        "examples/flow_lab/app.mjs",
        "examples/flow_lab/test_model.mjs",
    ), "node --test --test-reporter=tap examples/flow_lab/test_model.mjs", "executed"),
    "data-studio": Starter("interactive-visual-analytics", (
        "examples/data_studio/README.md",
        "examples/data_studio/index.html",
        "examples/data_studio/styles.css",
        "examples/data_studio/model.mjs",
        "examples/data_studio/app.mjs",
        "examples/data_studio/test_model.mjs",
    ), "node --test --test-reporter=tap examples/data_studio/test_model.mjs", "executed"),
    "ui-atlas": Starter("interactive-ui-pattern-atlas", (
        "examples/ui_atlas/README.md",
        "examples/ui_atlas/index.html",
        "examples/ui_atlas/styles.css",
        "examples/ui_atlas/model.mjs",
        "examples/ui_atlas/app.mjs",
        "examples/ui_atlas/test_model.mjs",
    ), "node --test --test-reporter=tap examples/ui_atlas/test_model.mjs", "executed"),
    "proof-gallery": Starter("public-engineering-proof-gallery", (
        "examples/proof_gallery/README.md",
        "examples/proof_gallery/index.html",
        "examples/proof_gallery/styles.css",
        "examples/proof_gallery/model.mjs",
        "examples/proof_gallery/app.mjs",
        "examples/proof_gallery/test_model.mjs",
    ), "node --test --test-reporter=tap examples/proof_gallery/test_model.mjs", "executed"),
    "technology-atlas": Starter("public-technology-atlas", (
        "examples/technology_atlas/README.md",
        "examples/technology_atlas/index.html",
        "examples/technology_atlas/styles.css",
        "examples/technology_atlas/data.mjs",
        "examples/technology_atlas/model.mjs",
        "examples/technology_atlas/app.mjs",
        "examples/technology_atlas/test_model.mjs",
    ), "node --test --test-reporter=tap examples/technology_atlas/test_model.mjs", "executed"),
    "typed-api": Starter("api-contracts", (
        "examples/typed_api_sdk/README.md",
        "examples/typed_api_sdk/service.py",
        "examples/typed_api_sdk/test_service.py",
    ), "python -B -m unittest discover -s examples/typed_api_sdk -v", "historical"),
    "rust-compiler": Starter("compiler-and-vm", (
        "projects/bounded-lang/README.md",
        "projects/bounded-lang/Cargo.toml",
        "projects/bounded-lang/Cargo.lock",
        "projects/bounded-lang/src/lib.rs",
        "projects/bounded-lang/tests/bindings.rs",
        "projects/bounded-lang/tests/compile_budget.rs",
        "projects/bounded-lang/tests/limits.rs",
        "projects/bounded-lang/tests/pipeline.rs",
    ), "cargo test --manifest-path projects/bounded-lang/Cargo.toml --locked --offline", "historical"),
}

class StarterError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _fail(code: str) -> None:
    raise StarterError(code)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source_inventory(root: Path, pin: str) -> tuple[dict, dict[str,dict]]:
    if not isinstance(pin, str) or not _HASH.fullmatch(pin):
        _fail("external_manifest_pin_required")
    try:
        verify_capabilities(root, pin)
        obj = json.loads((root / "SOURCE_MANIFEST.json").read_text("utf-8"))
    except (ClaimError, VerificationError, OSError, ValueError, UnicodeError):
        _fail("unverified_public_source")
    inventory = {entry['path']: entry for entry in obj['files']}
    if len(inventory) != len(obj['files']):
        _fail("duplicate_manifest_path")
    return obj, inventory


def _select(profiles: list[str], *, allow_historical: bool, claims: list[dict]) -> tuple[list[str],list[str],set[str]]:
    if not profiles:
        _fail("no_profile_selected")
    if len(profiles) > len(STARTERS):
        _fail("too_many_profiles")
    known = {c['id']: c for c in claims}
    if len(known) != len(claims):
        _fail("duplicated_claim")
    names = sorted(set(profiles))
    if len(names) != len(profiles):
        _fail("duplicate_profile")
    paths: set[str] = set()
    commands = []
    for name in names:
        if not isinstance(name, str) or not _ID.fullmatch(name) or name not in STARTERS:
            _fail("unknown_profile")
        item = STARTERS[name]
        published = known.get(item.claim)
        if not published or published['qualification'] != item.qualification:
            _fail("profile_proof_status_drift")
        if item.qualification != 'executed' and not allow_historical:
            _fail("explicit_historical_opt_in_required")
        paths.update(item.paths)
        commands.append(item.test_command)
    return names, commands, paths


def _plan(root: Path, pin: str, profiles: list[str], allow_historical: bool) -> tuple[dict,dict[str,bytes]]:
    metadata, inventory = _source_inventory(root, pin)
    claims_json = json.loads((root / "docs/PUBLIC_CAPABILITIES.json").read_text("utf-8"))
    names, commands, paths = _select(profiles, allow_historical=allow_historical, claims=claims_json['claims'])
    selected = {}
    total = 0
    for p in sorted(paths):
        row = inventory.get(p)
        if not row or row.get('mode') != '100644':
            _fail("missing_or_nonregular_public_file")
        f = root.joinpath(*p.split('/'))
        try:
            if not f.is_file() or f.is_symlink():
                _fail("missing_or_symlink_source")
            data = f.read_bytes()
        except OSError:
            _fail("source_read_failed")
        if len(data) != row['bytes'] or _sha(data) != row['sha256']:
            _fail("source_content_drift")
        total += len(data)
        if total > MAX_OUTPUT_BYTES:
            _fail("output_too_large")
        selected[p] = data
    manifest = {
        'schema': 1,
        'source': 'public_only_local_snapshot',
        'externally_pinned_source_manifest_sha256': pin,
        'profiles': names,
        'profile_qualification': {name: STARTERS[name].qualification for name in names},
        'files': [{'path':p,'bytes':len(selected[p]),'sha256':_sha(selected[p]),'mode':'100644'} for p in sorted(selected)],
        'tests_to_run_manually': commands,
        'tests_executed_by_generator': 0,
        'privacy_boundary': 'No private repository, credentials, client assets or deployment configuration is an input',
        'runtime_boundary': 'Public educational reference code only, not a production-ready service or a certification',
    }
    return manifest, selected


def _kit_readme(manifest: dict) -> bytes:
    lines = [
        '# Portable public engineering starter', '',
        'This folder was generated from a SHA-256-pinned public demonstration snapshot.',
        'It contains original public examples only. No private product code, environment files,',
        'credentials, unpublished designs, CI or deployment configuration were imported.', '',
        '## Selected profiles', '',
    ]
    for profile in manifest['profiles']:
        lines.append('- **'+profile+'** — '+manifest['profile_qualification'][profile]+' evidence; see bundled README and tests')
    lines.extend(['', '## Run the included tests yourself', ''])
    for command in manifest['tests_to_run_manually']:
        lines.append('```sh\n'+command+'\n```')
    lines.extend(['', '## Boundaries', '',
      'Generated bytes match the pinned source manifest and REUSE_MANIFEST.json.',
      'That does not prove authorship, legal reuse rights, security review, production',
      'deployment, native distributed operation, or current test execution.',
      'A historical profile needs explicit selection and has not been promoted to tested.', '',
      'Do not automatically combine this reference code with client or employer software.',
      'First review its license/ownership and required security, accessibility and runtime tests.', ''])
    return ('\n'.join(lines)).encode('utf-8')


def export_public_starter(root: Path, pin: str, profiles: list[str], destination: Path,
                          *, allow_historical: bool = False, dry_run: bool = False) -> dict:
    root = root.resolve(strict=True)
    destination = destination.absolute()
    if destination.name in {'.', '..'} or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,80}', destination.name):
        _fail("invalid_destination_name")
    parent = destination.parent
    if not parent.is_dir() or parent.is_symlink():
        _fail("unsafe_destination_parent")
    if destination.exists() or destination.is_symlink():
        _fail("destination_already_exists")
    if destination.resolve(strict=False).is_relative_to(root):
        _fail("destination_inside_source")
    manifest, sources = _plan(root, pin, profiles, allow_historical)
    receipt = {'status':'DRY_RUN' if dry_run else 'EXPORTED',
               'profiles':manifest['profiles'],'selected_files':len(sources),
               'payload_bytes':sum(len(x) for x in sources.values()),
               'output_manifest_sha256':None,'tests_executed':0}
    if dry_run:
        return receipt
    stage = Path(tempfile.mkdtemp(prefix='.public-starter-stage-',dir=parent))
    try:
        for p, raw in sources.items():
            target = stage.joinpath(*p.split('/'))
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw)
            target.chmod(stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IROTH)
            if target.read_bytes() != raw:
                _fail('staged_copy_mismatch')
        readme = _kit_readme(manifest)
        (stage/'README.md').write_bytes(readme)
        manifest['generated_readme_sha256'] = _sha(readme)
        blob = (json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
        (stage/'REUSE_MANIFEST.json').write_bytes(blob)
        # Reserve the destination *exclusively*. A plain rename could replace
        # a concurrently-created empty folder on POSIX, violating no-overwrite.
        try:
            destination.mkdir(mode=0o700)
        except FileExistsError:
            _fail('destination_concurrent_creation')
        try:
            for candidate in sorted(stage.rglob('*')):
                rel = candidate.relative_to(stage)
                dest = destination / rel
                if candidate.is_dir():
                    dest.mkdir(exist_ok=True)
                elif candidate.is_file() and not candidate.is_symlink():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with dest.open('xb') as output:  # Never overwrite any file.
                        output.write(candidate.read_bytes())
                else:
                    _fail('invalid_staged_file')
            receipt['output_manifest_sha256'] = _sha(blob)
        except Exception:
            # This routine created the output dir. An aborted export is not a kit.
            shutil.rmtree(destination)
            raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return receipt


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--expected-manifest-sha256',required=True)
    p.add_argument('--profile',action='append',default=[])
    p.add_argument('--all-executed',action='store_true')
    p.add_argument('--allow-historical',action='store_true')
    p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--dry-run',action='store_true')
    args=p.parse_args(argv)
    profiles=args.profile+([name for name,item in STARTERS.items() if item.qualification=='executed'] if args.all_executed else [])
    try:
        out=export_public_starter(args.root,args.expected_manifest_sha256,profiles,args.destination,
                                  allow_historical=args.allow_historical,dry_run=args.dry_run)
    except (StarterError, OSError, ValueError) as ex:
        out={'status':'FAIL','code':getattr(ex,'code','invalid_input')}
    print(json.dumps(out,sort_keys=True,indent=2))
    return 0 if out['status']!='FAIL' else 1


if __name__=='__main__':
    sys.exit(main())
