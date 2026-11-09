"""Run the frozen scope-aware conflicting-evidence engineering pilot v2."""
from __future__ import annotations
import argparse, asyncio
from pathlib import Path
from run_conflict_ablation import execute, load_frozen
from run_study import load_env_file

IMPLEMENTATION_FILES=(
 "conflict_ablation/models.py","conflict_ablation/generate_v2.py","conflict_ablation/arbiters.py",
 "conflict_ablation/store.py","run_conflict_ablation.py","run_conflict_ablation_pilot_v2.py",
 "analyze_conflict_ablation_pilot_v2.py","docs/CONFLICT_ABLATION_PILOT_V2_PROTOCOL.md")

async def main()->int:
 load_env_file(); p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--config",default="config/conflict_ablation_pilot_v2.json")
 p.add_argument("--db",default="results/conflict-ablation-pilot-v2.sqlite3")
 p.add_argument("--progress",default="results/conflict-ablation-pilot-progress-v2.txt")
 p.add_argument("--execute",action="store_true"); a=p.parse_args()
 spec,config,questions,freeze=load_frozen(Path(a.config),IMPLEMENTATION_FILES)
 print(f"Freeze: {spec['freeze_id']} | Pilot questions: {len(questions)}")
 if not a.execute: print("Validation passed. No API calls or writes made."); return 0
 await execute(spec,config,questions,freeze,a.db,a.progress); return 0
if __name__=="__main__": raise SystemExit(asyncio.run(main()))

