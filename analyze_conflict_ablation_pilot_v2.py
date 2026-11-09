"""Analyze engineering gates for conflict-ablation pilot v2."""
from __future__ import annotations
import argparse,sqlite3
from collections import Counter
from pathlib import Path
from conflict_ablation.models import ArbiterDecision
from run_conflict_ablation import load_frozen
from run_conflict_ablation_pilot_v2 import IMPLEMENTATION_FILES

def main()->int:
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--config",default="config/conflict_ablation_pilot_v2.json")
 p.add_argument("--db",default="results/conflict-ablation-pilot-v2.sqlite3"); p.add_argument("--output",default="results/conflict-ablation-pilot-analysis-v2.txt"); a=p.parse_args()
 spec,_,questions,freeze=load_frozen(Path(a.config),IMPLEMENTATION_FILES); db=sqlite3.connect(a.db)
 assert db.execute("SELECT value FROM meta WHERE key='freeze_hash'").fetchone()[0]==freeze
 correct=Counter(); totals=Counter(); positions=Counter(); complete=0
 for q in questions:
  decisions={(s,n):ArbiterDecision.model_validate_json(x) for s,n,x in db.execute("SELECT stage_index,arbiter,payload FROM decisions WHERE question_id=?",(q.id,))}; complete+=len(decisions)==12
  for stage in q.stages:
   winner=next(c for c in stage.candidates if c.is_correct); positions[winner.candidate_id]+=1
   for name in ("hash_tie","keyword_rule","openai","jev"):
    d=decisions.get((stage.stage_index,name))
    if d: totals[name]+=1; correct[name]+=d.selected_candidate_id==winner.candidate_id
 gates={"complete_at_least_29":complete>=29,"openai_at_least_81_of_90":correct["openai"]>=81,"jev_at_least_81_of_90":correct["jev"]>=81,"positions_exactly_30_each":positions=={"C1":30,"C2":30,"C3":30}}
 lines=["CONFLICT ABLATION PILOT V2",f"Freeze: {spec['freeze_id']}","Excluded from confirmation.","",f"Complete: {complete}/30"]+[f"{n}: {correct[n]}/{totals[n]}" for n in ("hash_tie","keyword_rule","openai","jev")]+["","ENGINEERING GATES"]+[f"{'PASS' if v else 'FAIL'}: {k}" for k,v in gates.items()]+["",f"OVERALL: {'PASS' if all(gates.values()) else 'FAIL'}",f"Failed calls: {db.execute('SELECT COUNT(*) FROM calls WHERE success=0').fetchone()[0]}",f"Recorded spend: ${db.execute('SELECT COALESCE(SUM(cost),0) FROM calls').fetchone()[0]:.4f}"]
 report="\n".join(lines)+"\n";Path(a.output).write_text(report,encoding="utf-8");print(report,end="");db.close();return 0
if __name__=="__main__":raise SystemExit(main())

