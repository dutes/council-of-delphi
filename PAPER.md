# When does a council help its judge? Two pre-registered studies of Delphi-style arbitration over LLM councils

**Brian Doutey**, independent researcher, Limerick, Ireland
Technical report, 20 November 2026. Code, data, frozen protocols and every scored run: this repository.

---

## Abstract

Multi-agent LLM systems, including debate, voting, reviewer chains and judge-arbitrated councils, are often justified by an appeal to the wisdom of crowds. However, LLM "crowds" are correlated, and a persuasive wrong answer can carry a group. I tested a bounded, Delphi-style procedure. Three models from three providers answer independently, and a structured judge (JEV, a commercial judgement API) decides whether the council stops or reconsiders once. The judge then selects the final answer. Every condition was paired on the same multiple-choice questions from MMLU-Pro and ARC-Challenge. The critical control was the judge answering each question alone.

**Study 1** (n = 494) used three small non-reasoning models. Its pre-registered primary result held: the judge-controlled Delphi process beat the council's majority vote by +13.2 points (95% CI +9.7 to +16.8). However, the judge alone scored 87.3% against Delphi's 80.8%, a post-hoc deficit of 6.5 points (95% CI +3.4 to +9.5).

**Study 2** (n = 500 fresh questions) was frozen before any scored call and stated in advance which result would falsify the generalisation. The small council replicated the deficit (+4.2 points in the judge's favour, 95% CI +1.2 to +7.2). A substantially stronger council (GPT-5.5, Claude Sonnet 5.5 and Mistral Medium 3.5, reasoning switched off) reversed it. Delphi scored 89.8% against the judge's 86.2%, a difference of −3.6 points (95% CI −6.2 to −1.0). Adding the judge's own answer as an anonymous candidate scored 91.0%, +4.8 points over the judge alone (95% CI +2.4 to +7.4).

The pattern is consistent with a simple account. A judge-arbitrated council can only beat its judge when the council's candidate set contains the right answer more often than the judge finds it alone. Below that point, the council costs the judge accuracy. Total API spend for both studies was about $41.

---

## 1. Introduction

Here is a concrete case from Study 1. Asked which rock guitarist designed a line of men's neckties, Claude Haiku 4.5 answered Jerry Garcia (correct) on two of three samples. Ministral 14B answered Brian May on all three, each time with a detailed and confident account of the ties, and GPT-4.1 mini answered John Mayer. The judge asked for reconsideration. All three models moved to Brian May, and the judge selected it. Answering alone, the same judge had chosen Jerry Garcia.

That question is one of 45 in Study 1 where the judge was right alone and wrong after arbitrating the council, against 13 in the opposite direction. It illustrates the tension this report is about. Aggregation and deliberation can recover answers that individual models miss. However, they can also import errors into a component that didn't have them.

Most evaluations of multi-agent setups compare the system against its weakest sensible baseline: a single model, or a majority vote. That comparison answers whether deliberation beats voting. It doesn't answer whether the system beats its own strongest component, and that's the question a practitioner deploying a judge actually faces. I designed both studies around that second comparison.

My contributions are:

1. A decomposition of a judge-arbitrated council into repeated sampling, cross-family voting, selection and one bounded round of reconsideration, with each step measured separately on paired questions.
2. A pre-registered replication, on fresh questions, showing that a weak council costs a strong judge accuracy.
3. A pre-registered falsification test, with the disconfirming outcome written down before the run, showing that a stronger council reverses the effect under the same judge and procedure.
4. Evidence that letting the judge contribute its own answer as an unlabelled candidate outperforms both the judge alone and pure arbitration.
5. A fully reproducible package: frozen, hashed protocols and implementations; every scored call stored in SQLite; analysis scripts that re-run without API access and refuse to run if a frozen file has changed.

## 2. Background and related work

**Delphi and the wisdom of crowds.** The Delphi method elicits independent expert judgements, feeds back anonymised summaries and allows revision over bounded rounds (Dalkey & Helmer, 1963). Its premise is the one Galton (1907) observed at a country fair: aggregating independent estimates can beat most individuals. Independence and diversity are the load-bearing assumptions (Surowiecki, 2004). LLM samples violate the first by construction, and models trained on overlapping corpora weaken the second.

**Self-consistency and ensembling.** Sampling several reasoning paths and taking a majority improves chain-of-thought accuracy (Wang et al., 2023). Its benefit depends on samples making uncorrelated errors, which is less likely when a model answers directly without reasoning.

**Multi-agent debate and aggregation.** Several instances debating over rounds can improve factuality and reasoning (Du et al., 2024; Liang et al., 2024). Layered aggregation across heterogeneous models can outperform its strongest member (Wang et al., 2024). Liang et al. already pair debaters with a judge that manages the debate. However, a systematic benchmark found that debate, in its current forms, does not reliably beat simpler strategies such as self-consistency and ensembling (Smit et al., 2024).

**LLM-as-judge and conformity.** Strong models can serve as scalable evaluators, with known position and verbosity biases (Zheng et al., 2023). Models also shift answers towards what a user or interlocutor asserts (Sharma et al., 2024), which is the mechanism by which a confident wrong candidate can pull a judge.

This work sits between these strands. The judge is a selector and stop-or-continue controller rather than a debater. It is evaluated against its own solo performance, under protocols frozen before any scored data existed.

## 3. Method

### 3.1 Questions

Each study used 500 four-to-ten-option multiple-choice questions: 400 from MMLU-Pro (Wang et al., 2024b) and 100 from ARC-Challenge (Clark et al., 2018). Health and law categories were excluded. Study 2's questions, and its separate 60-question calibration set, exclude every question used before, both by source row and by exact text. That includes Study 1's sample and quarantined exploratory work. Dataset files are SHA-256 hashed in the freeze configs (`config/study_v1.json`, `config/followup_v1.json`). Ground truth never leaves the local process: every model-facing object carries a dummy label.

### 3.2 Models

| Role | Study 1 | Study 2 |
|---|---|---|
| Small council | `gpt-4.1-mini-2025-04-14`, `claude-haiku-4-5-20251001`, `ministral-14b-2512` | Same (replication arm) |
| Strong council | — | `gpt-5.5-2026-04-23`, `claude-sonnet-5-5`, `mistral-medium-3-5` |
| Judge | JEV (`jev-latest`), TypeSafe AI's own "System One" judgement model | Same |

**Reasoning control.** Council models answer without hidden reasoning. In Study 1, only models with no reasoning mode were eligible. Study 2 admitted models that can reason, with reasoning switched off on every call:
- OpenAI GPT-5.5 and Mistral Medium 3.5 ran with `reasoning_effort: "none"`.
- Claude Sonnet 5.5 can't fully disable thinking, so it was sent `thinking: {"type": "between_tools"}`. With no tools in the request, that suppresses up-front thinking.
- Claude Opus 5.5 can't switch thinking off, so it was excluded.

Every response was checked. Reasoning tokens, a thinking block or a reasoning field failed the call. None of Study 2's 12,650 successful calls contained reasoning.

**Sampling.** Initial council answers use temperature 0.7 so that repeated samples can differ. The exception is Claude Sonnet 5.5, which rejects a temperature parameter and ran at Anthropic's fixed default. Every model has a 2,048-token output ceiling. Each answer is structured JSON: a label, a confidence and a short visible rationale. The rationale is evidence for the judge, not hidden chain-of-thought.

### 3.3 Conditions

For every question, the following are recorded. Letters follow the protocols.

- **A. First answers.** Sample 1 from each provider, one equal vote each.
- **B. Own crowd.** Three independent samples per provider; the plurality is that provider's position. Ties are broken by a seed-specific SHA-256 ordering frozen before any call.
- **C. Cross-model majority.** An equal vote over the three provider positions, with a 1-1-1 tie broken by a question-specific SHA-256 ordering. This is the non-judge baseline.
- **D. Judge alone.** The judge sees the question and choices only.
- **E. Selection only** (Study 1). Matching positions collapse into anonymised candidates carrying vote counts, rationales and confidences. The judge must select one and can't introduce a new answer. Unanimous councils pass through without a call.
- **F. Judge-controlled Delphi.** The judge assesses every council, unanimous ones included, selects the strongest current candidate and returns `stop` or `reconsider`. On `reconsider`, each council model receives the same anonymised candidate record. It is told the majority may be wrong and returns one revised position independently. The judge then selects among the revised positions. There is never a second round.
- **G. Delphi with the judge as a candidate** (Study 2). This is F with the strong council, reusing its council answers. The judge's own condition-D answer is inserted as one more anonymised candidate with a vote count of one, no rationale and no confidence. If it matches a council answer, it merges into that candidate. It remains in the list through the final selection, so reconsideration can't remove it, and only the judge can pass it over.

The judge never sees model identities, costs, the baseline's choice or the ground truth.

### 3.4 Strength matching in Study 2

TypeSafe doesn't publish JEV's architecture or size, so I matched on measured accuracy. On 60 calibration questions, disjoint from everything else, I measured the judge alone and the candidate models fixed in the config before calibration: four from OpenAI, three from Mistral and the Anthropic models that passed preflight. The frozen rule picks, per provider, the cheapest candidate within ±3 points of the judge. If none qualifies, it picks the closest and records the gap.

With reasoning off, no candidate came within 3 points. The judge scored 86.7% on calibration. The rule chose Claude Sonnet 5.5 (83.3%, −3.3 points), GPT-5.5 (75.0%, −11.7 points) and Mistral Medium 3.5 (63.3%, −23.3 points). I therefore describe this as a *strong* council, not a *matched* one. The protocol was amended before freezing to say so, and to add the strength comparison (F-strong minus F-small) as a secondary estimand. One candidate, `claude-sonnet-4-6`, was dropped for repeatedly breaking the output format: it wrote confidence as 99 instead of 0.99 and failed 4 of 60 questions on both attempts.

### 3.5 Estimands and analysis

| Study | Primary estimand (pre-registered) |
|---|---|
| 1 | F − C: Delphi minus cross-model majority |
| 2 | D − F-strong: judge alone minus strong-council Delphi |

Study 2's protocol stated the decision rule before the run:
- An interval entirely below zero means the Study 1 generalisation was wrong.
- An interval spanning zero leaves the question open.
- An interval entirely above zero means the council costs the judge even when much stronger.

All differences are paired, question-level accuracy differences. The 95% intervals are percentile intervals from a question-level bootstrap with 10,000 draws and the analysis seed fixed in the config. Study 2 has one primary estimand and no multiplicity correction; secondary estimands are labelled as such. A question missing a value in either condition is dropped from that comparison only, and the count is reported.

As a supplementary check that was not pre-registered, I report exact two-sided McNemar (binomial) p-values on the discordant pairs.

### 3.6 Operational safeguards

- **Freezing.** Protocols, implementation files and datasets were hashed and frozen before any scored call. The locked analysis scripts verify those hashes and refuse to run if anything has changed. Study 1's judge-alone-versus-Delphi comparison therefore lives in a separate post-hoc script (`analyze_posthoc.py`) rather than being edited into the locked one.
- **Blinding.** No interim accuracy was viewed during either run.
- **Failures.** Successful calls were never rerun. A missing stage gets at most two recorded attempts. More than 2% incomplete questions makes the primary analysis non-evaluable.
- **Cost cap.** A recorded-cost cap pauses execution between questions. Raising it is an operational amendment, stored in the results database and printed in the report.
- **Amendments,** all disclosed in the protocols:
  - Study 1 replaced `gemini-2.5-flash`, which was uncallable for new users, with `ministral-14b-2512` before any scored call.
  - Study 1 aborted its first start after six questions because a 512-token ceiling truncated JSON. That database was quarantined, the ceiling was raised to 2,048 tokens for all models, and the run restarted with no accuracy inspected.
  - Study 2 raised its $30 cap to $31 with two questions remaining.

## 4. Study 1: a small council

494 of 500 questions completed, with 41 failed calls. That is inside the 2% missingness limit.

### 4.1 Accuracy

| Condition | Accuracy |
|---|---|
| A. First answers, cross-model vote | 64.8% |
| C. Own crowds, cross-model vote (baseline) | 67.6% |
| E. Judge selection only | 73.5% |
| Simple vote over post-reconsideration positions | 76.7% |
| F. Judge-controlled Delphi | 80.8% |
| **D. Judge alone** | **87.3%** |

| Provider | First sample | Own crowd of three |
|---|---|---|
| GPT-4.1 mini | 62.6% | 63.6% (+1.0) |
| Claude Haiku 4.5 | 65.6% | 66.0% (+0.4) |
| Ministral 14B | 60.1% | 60.5% (+0.4) |

### 4.2 Paired comparisons

| Comparison | Difference [95% CI] | Discordant pairs | McNemar p |
|---|---|---|---|
| **F − C (primary)** | **+13.2 pp [+9.7, +16.8]** | 76 helpful / 11 harmful | < 10⁻¹² |
| B-vote − A-vote | +2.8 pp [+1.2, +4.7] | | |
| E − C | +5.9 pp [+3.0, +8.9] | | |
| D − F (post-hoc) | +6.5 pp [+3.4, +9.5] | 45 / 13 | 3 × 10⁻⁵ |

### 4.3 Process

- **Disagreement and reconsideration.** The council disagreed on 222 questions. The judge requested reconsideration on 220.
- **Candidate ceiling.** A correct provider position existed on 382 of 494 questions (77.3%). A correct raw sample existed among the nine on 409 (82.8%).
- **Selection.** When a correct position was available, selection-only picked it 95.0% of the time.

Two observations matter for interpretation.
- **Selection was not the bottleneck; coverage was.** The judge was an excellent selector, yet the initial candidate ceiling of 77.3% sat ten points below the judge's own accuracy.
- **Reconsideration pushed past that ceiling.** Full Delphi reached 80.8%, above the 77.3% ceiling, because revision created correct candidates that hadn't existed. However, it didn't close the gap to the judge alone.

Self-consistency was nearly inert. Three samples from a non-reasoning model added 0.4 to 1.0 points, which is consistent with highly correlated errors.

The D − F comparison was not pre-registered. I treated it as a hypothesis for Study 2, not a finding.

## 5. Study 2: replication and a strong council

All 500 questions completed for the primary comparison. 17 calls failed, almost all of them small-council JSON truncations, which left one question incomplete for the small-council arm (n = 499 there).

### 5.1 Accuracy

| Condition | n | Accuracy |
|---|---|---|
| F-small. Delphi, small council | 499 | 82.0% |
| C-strong. Strong council, majority vote | 500 | 82.8% |
| **D. Judge alone** | 500 | **86.2%** |
| F-strong. Delphi, strong council | 500 | 89.8% |
| **G. Delphi, strong council + judge as candidate** | 500 | **91.0%** |

| Council model | First sample | Own crowd of three |
|---|---|---|
| GPT-4.1 mini | 63.6% | 65.9% |
| Claude Haiku 4.5 | 68.2% | 67.9% |
| Ministral 14B | 60.7% | 60.3% |
| GPT-5.5 | 82.6% | 83.0% |
| Claude Sonnet 5.5 | 83.6% | 83.4% |
| Mistral Medium 3.5 | 69.0% | 70.0% |

### 5.2 Paired comparisons

| Comparison | Difference [95% CI] | Discordant pairs (first right only / second right only) | McNemar p |
|---|---|---|---|
| **D − F-strong (primary)** | **−3.6 pp [−6.2, −1.0]** | 13 / 31 | 0.0096 |
| D − F-small (replication) | +4.2 pp [+1.2, +7.2] | 40 / 19 | 0.0086 |
| G − D | +4.8 pp [+2.4, +7.4] | 32 / 8 | 0.0002 |
| F-strong − C-strong | +7.0 pp [+4.4, +9.8] | 42 / 7 | 4 × 10⁻⁷ |
| F-strong − F-small | +7.8 pp [+5.2, +10.6] | 44 / 5 | 8 × 10⁻⁹ |

The primary interval lies entirely below zero. By the rule I froze in advance, the Study 1 generalisation was wrong: its result was a property of a weak council, not of councils.

### 5.3 Process

| Arm | Reconsideration requested | Wrong → right | Right → wrong |
|---|---|---|---|
| F-small | 186 / 499 | 40 | 8 |
| F-strong | 114 / 500 | 19 | 6 |
| G | 113 / 500 | 20 | 4 |

- **Candidate ceiling.** The strong council produced a correct candidate on 450 of 500 questions (90.0%), above the judge's solo 86.2%. When a correct candidate existed, strong-council Delphi was correct 96.7% of the time.
- **Condition G.** The final answer equalled the judge's own answer on 451 of 500 questions. The 49 departures are where the council talked the judge round, and they account for the net gain over the judge alone (32 helpful against 8 harmful).

## 6. Supporting studies on synthetic evidence

I ran three smaller, separately frozen studies on synthetic questions with novel pseudonymous entities, so that no model could answer from training data. Each question required a three-link chain of facts. Each of three specialists held exactly one link, plus five distractors. I treat these as engineering checks: with full evidence the task is easy, and several conditions hit 100%. Protocols and locked analyses are in `docs/` and `results/`.

One result generalises beyond the plumbing, from `EVIDENCE_PROTOCOL.md` (n = 300):
- Specialists summarised their evidence into reports and the judge synthesised them: **12.7%** accuracy.
- That's below the judge answering with no evidence (26.0%, approximately chance on four options), a difference of −13.3 points [−19.3, −7.3].
- Given the raw evidence, the judge scored 100%.
- No report preserved all three support links (0 of 300).

Summaries didn't merely lose information; they misled. A follow-up that let the judge request specific evidence (active retrieval) recovered 100% (`ACTIVE_DELPHI_CONFIRMATORY_PROTOCOL.md`).

## 7. Discussion

### 7.1 A coverage account

The two studies are reconciled by comparing the council's candidate ceiling with the judge's solo accuracy.

| Setting | Correct candidate exists | Judge alone | Delphi | Delphi − judge |
|---|---|---|---|---|
| Study 1, small council | 77.3% | 87.3% | 80.8% | −6.5 |
| Study 2, strong council | 90.0% | 86.2% | 89.8% | +3.6 |

When the council's coverage is below the judge's own accuracy, arbitration can't win on selection. Reconsideration can generate new correct candidates. However, the judge also inherits the council's confident errors, as in the necktie example. When coverage exceeds the judge's accuracy and the judge selects well (95–97% when a correct candidate exists), the council adds answers the judge wouldn't have found.

The strong council's members scored between 69% and 84%, all below the judge's 86%. So the council didn't need to beat the judge member for member. It needed to be wrong on *different* questions. That fits the ensemble intuition: complementarity, not individual strength, is what the judge harvests.

This account is post-hoc and rests on two data points. It makes a testable prediction, though: the D − F difference should track the candidate ceiling minus the judge's solo accuracy across councils of graded strength.

### 7.2 Give the judge a vote

Condition G is a cheap design change with the largest effect. A judge that only arbitrates can discard an answer it already holds. Placing that answer in the pool, unlabelled and with no special weight, gave the best result: +4.8 points over the judge alone and +1.2 over strong-council Delphi. Anonymity matters to the interpretation. The judge kept its own answer on 451 questions because the evidence supported it, not because it recognised it.

### 7.3 Repetition versus strength

Repeated sampling from non-reasoning models moved accuracy by about one point at most, in both studies. Swapping the small council for the strong one moved Delphi accuracy by 7.8 points under an identical procedure. For practitioners, who sits on the council matters far more than how many times each member is asked.

### 7.4 Deliberation still beats voting

In both studies, judge-controlled Delphi beat the same council's majority vote by large margins: +13.2 points with the small council and +7.0 with the strong one. Arbitration is valuable relative to voting. The question this report raises is whether it's valuable relative to the arbiter.

### 7.5 Implications

- Evaluate a multi-agent pipeline against its strongest single component, not only against a vote or a weak single model.
- Treat adding a reviewer or council member as a quality decision. A weak member can lower system accuracy even under a strong judge.
- Let the arbiter contribute its own answer, anonymously, alongside the council's.
- Pass raw evidence rather than summaries between agents, or let the judge request evidence it needs.

## 8. Limitations and threats to validity

- **Scope.** The study used one judge, two council slates, one prompt template, one Delphi round and multiple-choice questions only. The results show that council strength matters in this setup. They don't show that councils always or never help, and they don't speak to open-ended generation.
- **Partly opaque judge.** JEV is TypeSafe's own model. Its documentation describes it as a "System One" model for fast, structured decisions, suited to judgements "a highly knowledgeable person could make in a few seconds", and recommends decomposing questions that need extended reasoning (TypeSafe AI, 2026). That positions it as a fast-judgement model rather than a reasoning one. However, its architecture is unpublished, so I can't rule out internal processing of a kind the council models had switched off. JEV beat every council model with reasoning off, GPT-5.5 included.
- **Not strength-matched.** No candidate came within 3 points of the judge on calibration, so the strong council is stronger, not equal. The 60-question calibration set also can't resolve a 3-point window: each question is worth 1.7 points, and the standard error is about 5 points. GPT-5.5 scored 75.0% on calibration and 82.6% on the main sample.
- **Heterogeneous "reasoning off".** Providers implement it differently. Sonnet 5.5 ran with `between_tools` rather than a true disable, and at Anthropic's default temperature rather than 0.7. Every response was verified free of reasoning output.
- **A recording error.** Study 2's freeze record labels Sonnet 5.5's setting as `reasoning_effort none`. The request the code sent was `thinking: {"type": "between_tools"}`, as the protocol text and `followup_study/providers.py` show. The label was produced by the freeze script, and no behaviour depended on it.
- **Post-hoc origin.** Study 1's judge-alone comparison was post-hoc. Study 2 was designed to test it, and its replication arm confirmed it on fresh questions.
- **Contamination.** MMLU-Pro and ARC questions may appear in training data. That applies to all conditions equally, but it could compress or inflate differences between models.
- **Supplementary statistics.** The McNemar p-values were not pre-registered. They agree with the bootstrap intervals in every case.
- **Amendments and missingness.** The model substitution, the aborted start, the cost-cap raise and the incomplete question are each disclosed above and recorded in the protocols or databases.

## 9. Reproducibility

Every scored call is stored in `results/*.sqlite3`. The analyses below need no API keys and make no network calls:

```bash
python analyze_study.py --config config/study_v1.json --db results/arbiter-study-v5.sqlite3 --output results/reanalysis-v5.txt
python analyze_posthoc.py
python analyze_followup.py --output results/reanalysis-followup-v1.txt
```

Each locked script verifies the frozen hashes before running. Re-running the Study 2 analysis on a second machine reproduced `results/followup-analysis-v1.txt` line for line. Setup and execution of new runs are in [`docs/RUNNING.md`](docs/RUNNING.md). The full protocols are [`docs/PROTOCOL.md`](docs/PROTOCOL.md) and [`docs/FOLLOWUP_PROTOCOL.md`](docs/FOLLOWUP_PROTOCOL.md).

| Study | Freeze ID | Recorded spend |
|---|---|---|
| 1 | `jev-crowd-council-delphi-2026-09-24-v5` | $5.65 (under $9 with the three supporting studies) |
| 2 | `delphi-followup-matched-council-v1` | $30.19, plus $2.08 calibration |

## 10. Conclusion

A judge-arbitrated LLM council is not a free improvement. With a weak council it cost a strong judge 4 to 6.5 points, a result that replicated on fresh questions. With a stronger council, under the same judge and procedure, it gained 3.6 points, and giving the judge an anonymous vote gained 4.8. The variable that decided the outcome was whether the council could put the right answer on the table more often than the judge could find it alone. I'd rather have learnt that by being wrong in public than by never testing it.

## References

- Clark, P., Cowhey, I., Etzioni, O., Khot, T., Sabharwal, A., Schoenick, C., & Tafjord, O. (2018). Think you have solved question answering? Try ARC, the AI2 Reasoning Challenge. *arXiv:1803.05457*.
- Dalkey, N., & Helmer, O. (1963). An experimental application of the Delphi method to the use of experts. *Management Science, 9*(3), 458–467.
- Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2024). Improving factuality and reasoning in language models through multiagent debate. *ICML 2024*. arXiv:2305.14325.
- Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
- Galton, F. (1907). Vox populi. *Nature, 75*, 450–451.
- Liang, T., He, Z., Jiao, W., Wang, X., Wang, Y., Wang, R., Yang, Y., Shi, S., & Tu, Z. (2024). Encouraging divergent thinking in large language models through multi-agent debate. *EMNLP 2024*. arXiv:2305.19118.
- Sharma, M., Tong, M., Korbak, T., et al. (2024). Towards understanding sycophancy in language models. *ICLR 2024*. arXiv:2310.13548.
- Smit, A. P., Grinsztajn, N., Duckworth, P., Barrett, T. D., & Pretorius, A. (2024). Should we be going MAD? A look at multi-agent debate strategies for LLMs. *ICML 2024*. arXiv:2311.17371.
- Surowiecki, J. (2004). *The Wisdom of Crowds*. Doubleday.
- TypeSafe AI (2026). Introduction. TypeSafe documentation. https://docs.typesafe.ai/introduction (accessed 23 November 2026).
- Wang, J., Wang, J., Athiwaratkun, B., Zhang, C., & Zou, J. (2024). Mixture-of-Agents enhances large language model capabilities. arXiv:2406.04692.
- Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., & Zhou, D. (2023). Self-consistency improves chain of thought reasoning in language models. *ICLR 2023*. arXiv:2203.11171.
- Wang, Y., Ma, X., Zhang, G., et al. (2024b). MMLU-Pro: A more robust and challenging multi-task language understanding benchmark. *NeurIPS 2024 Datasets and Benchmarks*. arXiv:2406.01574.
- Zheng, L., Chiang, W.-L., Sheng, Y., et al. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. *NeurIPS 2023 Datasets and Benchmarks*. arXiv:2306.05685.

---

*Independence: this is a personal, self-funded project. No person or organisation paid for, commissioned or influenced it. I have no affiliation with TypeSafe AI or any model provider.*
