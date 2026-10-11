#!/usr/bin/env python3
"""Run only the example suites, sequentially. Never install or deploy anything."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def execute(command: list[str], *, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=20, check=False)


def version(tool: str) -> str | None:
    executable = shutil.which(tool)
    if executable is None:
        return None
    result = execute([executable, '--version'])
    return result.stdout.strip() if result.returncode == 0 else None


def test_result(name: str, command: list[str], pattern: str, *, environment: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        result = execute(command, environment=environment)
    except subprocess.TimeoutExpired:
        return {"component": name, "status": "FAIL", "reason": "20-second subprocess limit exceeded"}
    output = result.stdout + result.stderr
    count = re.search(pattern, output)
    passed = result.returncode == 0 and count is not None and int(count.group(1)) > 0
    if not passed:
        print(output, file=sys.stderr)
    return {"component": name, "status": "PASS" if passed else "FAIL", "tests": int(count.group(1)) if count else None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--component', choices=['queue', 'eval', 'sdk'])
    group.add_argument('--demo', choices=['queue', 'eval', 'sdk'])
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        print('BLOCKED: Python 3.11 or newer is required.', file=sys.stderr)
        return 2
    if args.demo in ('queue', 'eval'):
        command = [sys.executable, '-B', 'examples/durable_jobs/demo.py'] if args.demo == 'queue' else [
            sys.executable, '-B', 'examples/ranking_eval/evaluation.py', 'examples/ranking_eval/synthetic.json', '--k', '2']
        result = execute(command)
        print(result.stdout, end=''); print(result.stderr, end='', file=sys.stderr)
        return result.returncode

    selected = [args.component or args.demo] if args.component or args.demo else ['queue', 'eval', 'sdk']
    environment = {'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version}
    results = []
    with tempfile.TemporaryDirectory(prefix='engineering-examples-') as temporary:
        for component in selected:
            if component in ('queue', 'eval'):
                directory = 'durable_jobs' if component == 'queue' else 'ranking_eval'
                results.append(test_result(component, [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', f'examples/{directory}', '-p', 'test_*.py', '-v'], r'Ran (\d+) tests?'))
                continue
            node_version, tsc_version = version('node'), version('tsc')
            environment.update(node=node_version, typescript=tsc_version)
            if node_version is None or tsc_version is None:
                results.append({'component': 'sdk', 'status': 'BLOCKED', 'reason': 'Node.js and an existing TypeScript compiler are required; nothing was installed.'})
                continue
            build = Path(temporary) / 'sdk'
            compiled = execute([shutil.which('tsc'), '--project', 'examples/read_client/tsconfig.json', '--outDir', str(build)])
            if compiled.returncode != 0:
                print(compiled.stdout + compiled.stderr, file=sys.stderr)
                results.append({'component': 'typescript', 'status': 'FAIL'})
                continue
            results.append({'component': 'typescript', 'status': 'PASS', 'scope': 'strict compilation and compile-only type assertions'})
            if args.demo == 'sdk':
                result = execute([shutil.which('node'), str(build / 'demo.mjs')])
                print(result.stdout, end=''); print(result.stderr, end='', file=sys.stderr)
                return result.returncode
            child_environment = os.environ.copy()
            child_environment['SDK_MODULE'] = str(build / 'client.mjs')
            results.append(test_result('sdk', [shutil.which('node'), '--test', '--test-concurrency=1', 'examples/read_client/client.test.mjs'], r'# tests (\d+)', environment=child_environment))
    print(json.dumps({'scope': 'isolated example tests; one loopback HTTP test; no external service calls', 'environment': environment, 'results': results}, indent=2, sort_keys=True))
    if any(item['status'] == 'FAIL' for item in results):
        return 1
    if any(item['status'] == 'BLOCKED' for item in results):
        return 2
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, subprocess.TimeoutExpired):
        print('BLOCKED: a required local tool was unavailable or exceeded its time limit.', file=sys.stderr)
        raise SystemExit(2)
