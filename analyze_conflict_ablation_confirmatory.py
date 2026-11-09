"""Locked paired analysis for the conflicting-evidence arbiter confirmation."""
from __future__ import annotations
import argparse,random,sqlite3
from collections import Counter
from pathlib import Path
from statistics import mean
from conflict_ablation.models import ArbiterDecision
from run_conflict_ablation import load_frozen
from run_conflict_ablation_confirmatory import IMPLEMENTATION_FILES

ARBITERS=("hash_tie","keyword_rule","openai","jev")
def interval(values,draws,seed):
 rng=random.Random(seed);est=sorted(mean(rng.choice(values) for _ in values) for _ in range(draws))
 return mean(values),est[int(.025*draws)],est[int(.975*draws)-1]

def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--config",default="config/conflict_ablation_confirmatory_v1.json")
 p.add_argument("--db",default="results/conflict-ablation-confirmatory-v1.sqlite3");p.add_argument("--output",default="results/conflict-ablation-confirmatory-analysis-v1.txt");a=p.parse_args()
 spec,_,questions,freeze=load_frozen(Path(a.config),IMPLEMENTATION_FILES);db=sqlite3.connect(Path(a.db).resolve().as_uri()+"?mode=ro",uri=True)
 assert db.execute("SELECT value FROM meta WHERE key='freeze_hash'").fetchone()[0]==freeze
 rows=[];stage_correct=Counter();stage_total=Counter()
 for q in questions:
  decisions={(s,n):ArbiterDecision.model_validate_json(x) for s,n,x in db.execute("SELECT stage_index,arbiter,payload FROM decisions WHERE question_id=?",(q.id,))}
  if len(decisions)!=12:continue
  path={name:True for name in ARBITERS}
  for stage in q.stages:
   winner=next(c.candidate_id for c in stage.candidates if c.is_correct)
   for name in ARBITERS:
    hit=decisions[(stage.stage_index,name)].selected_candidate_id==winner
    stage_total[name]+=1;stage_correct[name]+=hit;path[name]&=hit
  rows.append(path)
 n=len(rows);evaluable=(len(questions)-n)/len(questions)<=spec["maximum_missing_fraction"]
 contrasts={"JEV minus keyword rule":[int(r["jev"])-int(r["keyword_rule"]) for r in rows],"JEV minus OpenAI classifier":[int(r["jev"])-int(r["openai"]) for r in rows],"JEV minus hash tie":[int(r["jev"])-int(r["hash_tie"]) for r in rows]}
 cis={name:interval(values,spec["bootstrap_draws"],spec["analysis_seed"]+i) for i,(name,values) in enumerate(contrasts.items())}
 openai_ci=cis["JEV minus OpenAI classifier"];margin=spec["equivalence_margin"]
 equivalent=openai_ci[1]>-margin and openai_ci[2]<margin
 lines=["CONFLICTING-EVIDENCE ARBITER CONFIRMATION - LOCKED ANALYSIS","="*65,f"Freeze: {spec['freeze_id']}",f"Complete: {n}/{len(questions)}",f"Evaluable: {'YES' if evaluable else 'NO'}","","FULL THREE-STAGE PATH ACCURACY"]
 lines += [f"{name}: {100*mean(r[name] for r in rows):.2f}%" for name in ARBITERS]
 lines += ["","STAGE SELECTION ACCURACY"]+[f"{name}: {stage_correct[name]}/{stage_total[name]} ({100*stage_correct[name]/stage_total[name]:.2f}%)" for name in ARBITERS]
 lines += ["","PAIRED QUESTION-LEVEL EFFECTS"]+[f"{name}: {100*x[0]:+.2f} pp [{100*x[1]:+.2f}, {100*x[2]:+.2f}]" for name,x in cis.items()]
 lines += [f"JEV/OpenAI descriptive ±{100*margin:.0f} pp equivalence criterion: {'MET' if equivalent else 'NOT MET'}","",f"Failed calls: {db.execute('SELECT COUNT(*) FROM calls WHERE success=0').fetchone()[0]}",f"Recorded spend: ${db.execute('SELECT COALESCE(SUM(cost),0) FROM calls').fetchone()[0]:.4f}"]
 report="\n".join(lines)+"\n";Path(a.output).write_text(report,encoding="utf-8");print(report,end="");db.close();return 0
if __name__=="__main__":raise SystemExit(main())

