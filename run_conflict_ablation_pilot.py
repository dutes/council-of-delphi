"""Run the frozen 30-question conflicting-evidence engineering pilot."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from run_conflict_ablation import execute, hash_files, load_frozen
from run_study import load_env_file


IMPLEMENTATION_FILES = (
    "conflict_ablation/models.py", "conflict_ablation/generate.py",
    "conflict_ablation/arbiters.py", "conflict_ablation/store.py",
    "run_conflict_ablation.py", "run_conflict_ablation_pilot.py",
    "analyze_conflict_ablation_pilot.py", "docs/CONFLICT_ABLATION_PILOT_PROTOCOL.md",
)


async def main() -> int:
    load_env_file()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/conflict_ablation_pilot_v1.json")
    parser.add_argument("--db", default="results/conflict-ablation-pilot-v1.sqlite3")
    parser.add_argument("--progress", default="results/conflict-ablation-pilot-progress-v1.txt")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    spec, config, questions, freeze_hash = load_frozen(Path(args.config), IMPLEMENTATION_FILES)
    print(f"Freeze: {spec['freeze_id']} | Pilot questions: {len(questions)}")
    if not args.execute:
        print("Validation passed. No API calls or result writes made.")
        return 0
    await execute(spec, config, questions, freeze_hash, args.db, args.progress)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

