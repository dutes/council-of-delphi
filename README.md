# Council of Delphi

**Does a council of LLMs, steered by a structured judge, beat the judge on its own?**

It depends on the council, and finding that out changed my mind.

I built this to test an idea that sounds obviously right: if one model can be wrong, ask several, let them see each other's reasoning, and have a judge decide when they should think again. It's the Delphi method, applied to LLMs. I ran it twice. Both studies were pre-registered, with the data and code frozen before any scored run, and I've reported every result, including the ones that went against me.

This page is the overview. The full technical report, with related work, methods, statistics and my account of why the result flips, is [`PAPER.md`](PAPER.md).

## The short version

**Study 1: a council of three small models** (494 questions from MMLU-Pro and ARC-Challenge).

- The judge-controlled Delphi process beat the council's own majority vote by **+13.2 points** (95% CI +9.7 to +16.8). That was the pre-registered primary result, and it held.
- However, the judge **on its own** scored **87.3%**, and the Delphi process it ran scored **80.8%**. Adding the council made the judge worse by **6.5 points**. I hadn't pre-registered that comparison, so I treated it as a finding to test, not a conclusion.

**Study 2: the follow-up** (500 new questions). Is the council the problem, or just *that* council? This time the main question was set in advance, along with exactly what would change my mind.

- With the **same small council**, the judge alone beat the Delphi process again, by **4.2 points** (95% CI +1.2 to +7.2). The first result replicated.
- With a **strong council** (GPT-5.5, Claude Sonnet 5.5 and Mistral Medium 3.5, all with reasoning switched off), the Delphi process **beat the judge alone by 3.6 points**: 89.8% against 86.2% (95% CI 1.0 to 6.2). That's the outcome I'd committed in writing to treat as proof I was wrong to generalise.
- Letting the judge's own answer sit anonymously among the candidates did best of all: **91.0%**, **4.8 points** above the judge alone.

So a weak council drags a good judge down, a strong one lifts it, and a judge that can weigh its own answer alongside a strong council does better than either alone.

## Why I ran it

Multi-agent setups are everywhere right now: debate, voting, councils, reviewers checking reviewers. The pitch is wisdom of crowds. However, a crowd of LLMs isn't a crowd of independent people. Samples from one model are correlated, models from different vendors share training data, and a persuasive wrong answer can pull the room with it.

I wanted to separate three things that usually get bundled together:

1. **Repeated sampling** from one model (a homogeneous crowd)
2. **Voting across model families** (a heterogeneous council)
3. **Arbitration**, where a judge picks the best-supported answer and decides whether the council should reconsider

Each step either adds accuracy or it doesn't. I measured each one separately.

## How it works (study 1)

```text
question
  -> each of 3 models answers 3 times independently       (9 samples)
  -> each model's own majority                            (3 positions)
  -> equal vote across the 3 models                       (crowd majority: the baseline)
  -> JEV assesses the council: stop, or reconsider once
       -> if reconsider: each model sees the anonymised candidates, is told
          the majority may be wrong, and gives one revised answer
  -> JEV selects the final answer                         (full Delphi)
```

**The council:** OpenAI `gpt-4.1-mini-2025-04-14`, Anthropic `claude-haiku-4-5-20251001` and Mistral `ministral-14b-2512`. All three run with hidden reasoning disabled, at temperature 0.7, with identical prompts and output limits.

**The judge:** JEV, TypeSafe AI's own structured-judgement model. Its [documentation](https://docs.typesafe.ai/introduction) describes it as a fast "System One" model for quick, structured decisions. It sees the question, the anonymised candidate answers, vote counts and short rationales. It never sees model identities or the ground truth.

**The control that matters:** JEV also answers every question on its own, with no council input. Without that, you can't tell whether a judge is good at *arbitrating* or just good at *answering*.

## Study 1 results

| Condition | Accuracy |
|---|---|
| Three first answers, cross-model vote | 64.8% |
| Three model crowds, cross-model vote (baseline) | 67.6% |
| JEV selecting from council positions only | 73.5% |
| Simple vote after JEV-triggered reconsideration | 76.7% |
| Full JEV-controlled Delphi | 80.8% |
| **JEV alone** | **87.3%** |

Paired differences, with 95% question-bootstrap intervals:

| Comparison | Difference |
|---|---|
| Full Delphi vs crowd majority (primary) | **+13.2 pp** [+9.7, +16.8] |
| Model crowds vs first answers | +2.8 pp [+1.2, +4.7] |
| JEV selection vs crowd majority | +5.9 pp [+3.0, +8.9] |
| JEV alone vs full Delphi (post-hoc) | **+6.5 pp** [+3.4, +9.5] |

A few things stand out:

- **Self-consistency barely helped.** Taking a majority of three samples improved each model by between 0.4 and 1.0 points. Repeated sampling from a non-reasoning model mostly repeats the same mistake.
- **The judge was an excellent selector.** When a correct answer existed among the council's positions, JEV picked it 95% of the time. The problem is that a correct position only existed on 382 of 494 questions. A judge can't select an answer nobody gave.
- **Reconsideration worked, but not enough.** JEV asked for a second round on 220 questions. That lifted the council, and still didn't close the gap to JEV answering alone.

## The follow-up: what if the council is strong?

Study 1 left an obvious objection: of course a strong judge gets worse when it has to listen to weaker models. Picture a good referee forced to consult three linesmen with bad eyesight. So I wrote a [follow-up protocol](docs/FOLLOWUP_PROTOCOL.md) to test that directly, and froze it before the run.

**The design.** Same judge, same Delphi procedure, same prompts, 500 new questions. Four conditions ran on every question:

- JEV alone
- Delphi with the original small council (a replication of study 1)
- Delphi with a strong council
- Delphi with the strong council, plus JEV's own answer added as one more anonymous candidate

**Choosing the strong council.** TypeSafe doesn't publish JEV's architecture or size, so I matched on measured accuracy instead. On 60 separate calibration questions, I measured JEV and nine candidate models, and picked from each provider the cheapest model within 3 points of JEV. Reasoning stayed switched off, as in study 1. With reasoning on, the strongest models leave a judge little to add. With it off, no model came within 3 points, so the rule fell back to the closest model from each provider. The strong council was a big step up, but it wasn't JEV's equal, and the protocol says so.

**Results**

| Condition | Accuracy |
|---|---|
| Delphi, original small council | 82.0% |
| Strong council, simple majority vote | 82.8% |
| **JEV alone** | **86.2%** |
| Delphi, strong council | 89.8% |
| **Delphi, strong council plus JEV as a candidate** | **91.0%** |

| Comparison | Difference |
|---|---|
| JEV alone vs Delphi with the strong council (primary) | **−3.6 pp** [−6.2, −1.0] |
| JEV alone vs Delphi with the small council (replication) | +4.2 pp [+1.2, +7.2] |
| Delphi with JEV as a candidate vs JEV alone | **+4.8 pp** [+2.4, +7.4] |
| Delphi vs majority vote, strong council | +7.0 pp [+4.4, +9.8] |
| Strong council vs small council, both under Delphi | +7.8 pp [+5.2, +10.6] |

**What I take from it:**

- **Council strength decides whether a council helps.** Same judge, same process, stronger council: almost 8 points better. Study 1's result was real, but it was a result about weak councils.
- **The strong council didn't need to match the judge to help it.** Its models scored between 69% and 84% on their own, against JEV's 86%. My reading is that different models get different questions wrong, and the process pooled what each one got right.
- **The judge still earns its place.** The strong council's own majority vote scored 82.8%. With JEV running the process, it reached 89.8%.
- **Reconsideration helps more than it hurts.** With the strong council, JEV asked for a second round on 114 questions. That turned 19 wrong answers right and 6 right answers wrong.
- **Give the judge a vote.** When JEV's own answer was an anonymous candidate, the final answer matched it on 451 of 500 questions. The other 49 are where the council talked it round, and that's where the extra accuracy came from.



I ran three smaller studies on synthetic data to test the plumbing of evidence routing. I treat them as engineering checks, not headline findings: the tasks were built so that full evidence makes them easy, and several conditions hit 100%.

One result from them is worth keeping. When specialists **summarised** their evidence before passing it to the judge, JEV's accuracy fell to **12.7%**. That's below the 25% you'd get by guessing on a four-option question, and below JEV answering with no evidence at all (26.0%). Given the raw evidence instead, it scored 100%. Lossy summaries didn't just lose information; they actively misled the judge. If you're designing a multi-agent pipeline, that's the finding I'd take away: pass evidence, not opinions about evidence.

The protocols for these are in `docs/` (`EVIDENCE_PROTOCOL.md`, `ACTIVE_DELPHI_*`, `CONFLICT_ABLATION_*`).

## Limitations

I'd rather state these plainly than have a reader find them:

- **One judge, two model slates, one prompt, one question mix.** The results apply to this setup. They show that council strength matters here; they don't show that councils always or never help.
- **What's inside JEV isn't public.** JEV is TypeSafe's own model. Its [documentation](https://docs.typesafe.ai/introduction) describes it as a fast "System One" model for judgements "a highly knowledgeable person could make in a few seconds", and advises splitting anything that needs extended reasoning into simpler questions. However, TypeSafe doesn't publish its architecture, so I can't rule out internal processing that the council models had switched off. JEV beat every council model with reasoning off, GPT-5.5 included.
- **The strong council wasn't matched to the judge.** No candidate came within 3 points of JEV on calibration, so the closest from each provider was chosen. The calibration step also used only 60 questions, which can't resolve a 3-point gap (each question is worth 1.7 points). GPT-5.5 scored 75% on calibration and 83% across the full 500.
- **"Reasoning off" means different settings for different providers.** GPT-5.5 and Mistral Medium 3.5 ran with `reasoning_effort: "none"`. Claude Sonnet 5.5 can't fully disable thinking, so it ran with `thinking: "between_tools"`, which turns off up-front thinking. Every response was checked, and none of the 12,650 successful calls in the follow-up contained reasoning. Sonnet 5.5 also rejects a temperature setting, so it ran at Anthropic's default instead of 0.7. One error to own: the follow-up's frozen freeze record labels Sonnet 5.5's setting as `reasoning_effort none`. The request the code actually sent is `thinking: "between_tools"`, as the protocol's text and `followup_study/providers.py` show.
- **Public benchmarks.** MMLU-Pro and ARC questions may appear in the models' training data.
- **Model substitution before the run.** Google's `gemini-2.5-flash` was the planned third model, but its API rejected new users during preflight. Mistral Large 3 was blocked by my subscription tier, so I used Ministral 14B, the strongest available Mistral model without reasoning mode. No scored data was produced before the swap.
- **One aborted start.** The first run was stopped after six questions because a 512-token output limit truncated JSON responses. I quarantined that database, raised the limit to 2,048 tokens for all models, and restarted. Nothing else changed, and no accuracy was inspected.
- **Incomplete questions.** In study 1, 494 of 500 questions completed, with 41 failed calls, inside the 2% limit I set in advance. In the follow-up, all 500 completed for the primary comparison. 17 calls failed, almost all of them small-council answers cut off mid-JSON, which left one question incomplete for the small council.
- **One cost-cap amendment.** The follow-up's $30 cap paused the run with 2 questions left. I raised it to $31 to finish them. The analysis report records the change, the time and the reason.

Full details are in [`docs/PROTOCOL.md`](docs/PROTOCOL.md) and [`docs/FOLLOWUP_PROTOCOL.md`](docs/FOLLOWUP_PROTOCOL.md).

## Rigour, on a budget

- Protocols written and frozen before any scored call
- Dataset and implementation hashed at freeze
- Ground truth never sent to any model
- No interim accuracy viewed during runs
- Earlier exploratory experiments quarantined under `archived/` and never pooled with these results
- Every scored run is stored as a SQLite database in `results/`, so the analysis can be re-run without new API calls

Total recorded API spend: **under $9** for study 1 and its three supporting studies, and **$32.27** for the follow-up, including calibration. Rigorous evaluation doesn't need a lab budget. It needs discipline about what you decide before you look.

## Reproducing it

Setup, preflight and execution instructions are in [`docs/RUNNING.md`](docs/RUNNING.md). Re-running the analysis on the stored results needs no API keys and makes no network calls:

```bash
python analyze_study.py --config config/study_v1.json --db results/arbiter-study-v5.sqlite3 --output results/reanalysis-v5.txt
python analyze_posthoc.py
```

The first command reproduces the locked, pre-registered report. It refuses to run if any frozen file has changed, so the post-hoc comparison lives in its own script rather than being edited into the locked one.

The follow-up's locked analysis works the same way:

```bash
python analyze_followup.py --output results/reanalysis-followup-v1.txt
```

I re-ran it from the stored database on a second machine, and it matched the original report line for line.

## Data

- [MMLU-Pro](https://github.com/TIGER-AI-Lab/MMLU-Pro) (TIGER-Lab), MIT licence
- [ARC-Challenge](https://allenai.org/data/arc) (Allen Institute for AI), CC BY-SA 4.0

Health and law categories were excluded.

## Licence

The code and documents are MIT licensed. The benchmark questions keep their original licences; see [`LICENSE`](LICENSE).

## Independence

This is a personal, self-funded project. No person or organisation paid for, commissioned or influenced it. I have no affiliation with TypeSafe AI or any model provider.

**Brian Doutey**, independent researcher, Limerick, Ireland
