from collections import Counter
from conflict_ablation.arbiters import keyword_rule
from conflict_ablation.generate_v2 import generate_question

def test_v2_balances_positions_and_labels():
 qs=[generate_question(i,20261020,prefix="test") for i in range(300)]
 assert Counter(q.correct_label for q in qs)=={x:75 for x in "ABCD"}
 positions=Counter(next(c for c in s.candidates if c.is_correct).candidate_id for q in qs for s in q.stages)
 assert positions=={"C1":300,"C2":300,"C3":300}

def test_v2_is_semantically_distinct_from_keyword_ceiling():
 qs=[generate_question(i,20261020,prefix="test") for i in range(10)]
 hits=sum(keyword_rule(s).selected_candidate_id==next(c for c in s.candidates if c.is_correct).candidate_id for q in qs for s in q.stages)
 assert hits<20

