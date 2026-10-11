#!/usr/bin/env python3
"""Source-pinned, non-overwriting public reference recipes for common work.

Only hand-authored, previously qualified PUBLIC profiles are ever selected.
Private repositories, company data and credentials are not accepted as inputs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Final

from export_public_starter import STARTERS
from one_shot_public_project import assemble


RECIPES: Final[dict[str, tuple[str, ...]]] = {
    "ai-search": ("agent", "retrieval", "evaluation", "training"),
    "service-foundation": ("jobs", "ledger", "policy"),
    "event-platform": ("jobs", "event-outbox", "policy", "proof-platform"),
    "full-reference": (
        "agent", "evaluation", "event-outbox", "jobs", "ledger", "policy",
        "proof-platform", "retrieval", "training",
    ),
}

class RecipeError(ValueError):
    pass


def select_recipe(recipe: str) -> list[str]:
    if type(recipe) is not str or recipe not in RECIPES:
        raise RecipeError("unknown_public_recipe")
    selected = list(RECIPES[recipe])
    if len(selected) != len(set(selected)):
        raise RecipeError("duplicate_profile_in_recipe")
    if any(name not in STARTERS or STARTERS[name].qualification != "executed"
           for name in selected):
        raise RecipeError("unqualified_public_recipe")
    return selected


def compose(root: Path, source_pin: str, recipe: str, destination: Path,
            *, receipt: Path | None = None, dry_run: bool = False,
            run_tests: bool = True) -> dict:
    try:
        profiles = select_recipe(recipe)
    except RecipeError as exc:
        return {"status": "FAIL", "stage": "recipe", "code": str(exc),
                "tested_groups": 0, "no_production_claim": True}
    result = assemble(root, source_pin, destination, profiles, run_tests=run_tests,
                      receipt=receipt, dry_run=dry_run)
    if result["status"] in ("PASS_TESTED", "PASS_VERIFIED_ONLY", "DRY_RUN"):
        result["recipe"] = recipe
        # The authoritative acceptance receipt is written BY assemble and is
        # not modified after creation. Recipe identity belongs to the CLI's
        # explanatory result, not a forged addition to that pinned receipt.
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--recipe", required=True, choices=sorted(RECIPES))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-tests", action="store_true")
    args = parser.parse_args(argv)
    result = compose(args.root, args.expected_source_sha256, args.recipe,
                     args.destination, receipt=args.receipt, dry_run=args.dry_run,
                     run_tests=not args.no_tests)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] in ("PASS_TESTED", "PASS_VERIFIED_ONLY", "DRY_RUN") else 1


if __name__ == "__main__":
    raise SystemExit(main())
