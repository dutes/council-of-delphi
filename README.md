# Council of Delphi

**Does a council of small LLMs, steered by a structured judge, beat the judge on its own?**

No. And I think that's the most interesting thing this project found.

I built this to test an idea that sounds obviously right: if one model can be wrong, ask several, let them see each other's reasoning, and have a judge decide when they should think again. It's the Delphi method, applied to LLMs. I pre-registered the study, froze the data and code before any scored run, and reported every result, including the ones that went against me.

## The short version

On 494 multiple-choice questions from MMLU-Pro and ARC-Challenge:

- The judge-controlled Delphi process beat the council's simple majority vote by **+13.2 points** (95% CI +9.7 to +16.8). That was my pre-registered primary result, and it held.
- However, the judge **on its own** scored **87.3%**. The full Delphi process scored **80.8%**. Adding the council made the judge worse by **6.5 points** (95% CI +3.4 to +9.5). I didn't pre-register that comparison; I added it after the locked analysis, because the JEV-alone control made the question impossible to ignore.
- On 45 questions the judge was right alone and the council process got it wrong. The reverse happened 13 times.

So the judge rescued a weak council, and the council then dragged the judge down. If you have a strong model available, wrapping it in a committee of weaker ones cost accuracy here, not gained it.

## Why I ran it

Multi-agent setups are everywhere right now: debate, voting, councils, reviewers checking reviewers. The pitch is wisdom of crowds. However, a crowd of LLMs isn't a crowd of independent people. Samples from one model are correlated, models from different vendors share training data, and a persuasive wrong answer can pull the room with it.

I wanted to separate three things that usually get bundled together:

1. **Repeated sampling** from one model (a homogeneous crowd)
2. **Voting across model families** (a heterogeneous council)
3. **Arbitration**, where a judge picks the best-supported answer and decides whether the council should reconsider

Each step either adds accuracy or it doesn't. I measured each one separately.

## How it works

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

**The judge:** JEV, a commercial structured-judgement API from TypeSafe AI. It sees the question, the anonymised candidate answers, vote counts and short rationales. It never sees model identities or the ground truth.

**The control that matters:** JEV also answers every question on its own, with no council input. Without that, you can't tell whether a judge is good at *arbitrating* or just good at *answering*.

## Results

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

## Supporting experiments

I ran three smaller studies on synthetic data to test the plumbing of evidence routing. I treat them as engineering checks, not headline findings: the tasks were built so that full evidence makes them easy, and several conditions hit 100%.

One result from them is worth keeping. When specialists **summarised** their evidence before passing it to the judge, JEV's accuracy fell to **12.7%**. That's below the 25% you'd get by guessing on a four-option question, and below JEV answering with no evidence at all (26.0%). Given the raw evidence instead, it scored 100%. Lossy summaries didn't just lose information; they actively misled the judge. If you're designing a multi-agent pipeline, that's the finding I'd take away: pass evidence, not opinions about evidence.

The protocols for these are in `docs/` (`EVIDENCE_PROTOCOL.md`, `ACTIVE_DELPHI_*`, `CONFLICT_ABLATION_*`).

## Limitations

I'd rather state these plainly than have a reader find them:

- **The council and the judge aren't equally capable.** The council is three small, fast models. TypeSafe doesn't publish which model powers JEV, and I've asked. Part of the "judge beats council" result may simply be that a stronger model beats weaker ones. A council of frontier models could behave differently, and that's what the [follow-up study](docs/FOLLOWUP_PROTOCOL.md) tests.
- **One model slate, one prompt, one question mix.** The results apply to this setup. They don't show that councils never help.
- **Public benchmarks.** MMLU-Pro and ARC questions may appear in the models' training data.
- **Model substitution before the run.** Google's `gemini-2.5-flash` was the planned third model, but its API rejected new users during preflight. Mistral Large 3 was blocked by my subscription tier, so I used Ministral 14B, the strongest available Mistral model without reasoning mode. No scored data was produced before the swap.
- **One aborted start.** The first run was stopped after six questions because a 512-token output limit truncated JSON responses. I quarantined that database, raised the limit to 2,048 tokens for all models, and restarted. Nothing else changed, and no accuracy was inspected.
- **Incomplete questions.** 494 of 500 questions completed, with 41 failed calls across the run. That's inside the 2% missingness limit I set in advance.

Full details are in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## Rigour, on a budget

- Protocols written and frozen before any scored call
- Dataset and implementation hashed at freeze
- Ground truth never sent to any model
- No interim accuracy viewed during runs
- Earlier exploratory experiments quarantined under `archived/` and never pooled with these results
- Every scored run is stored as a SQLite database in `results/`, so the analysis can be re-run without new API calls

Total recorded API spend for the four scored studies: **under $9**. Rigorous evaluation doesn't need a lab budget. It needs discipline about what you decide before you look.

## Reproducing it

Setup, preflight and execution instructions are in [`docs/RUNNING.md`](docs/RUNNING.md). Re-running the analysis on the stored results needs no API keys and makes no network calls:

```bash
python analyze_study.py --config config/study_v1.json --db results/arbiter-study-v5.sqlite3 --output results/reanalysis-v5.txt
python analyze_posthoc.py
```

The first command reproduces the locked, pre-registered report. It refuses to run if any frozen file has changed, so the post-hoc comparison lives in its own script rather than being edited into the locked one.

## Data

- [MMLU-Pro](https://github.com/TIGER-AI-Lab/MMLU-Pro) (TIGER-Lab), MIT licence
- [ARC-Challenge](https://allenai.org/data/arc) (Allen Institute for AI), CC BY-SA 4.0

Health and law categories were excluded.

## Licence

The code and documents are MIT licensed. The benchmark questions keep their original licences; see [`LICENSE`](LICENSE).

## Independence

This is a personal, self-funded project. No person or organisation paid for, commissioned or influenced it. I have no affiliation with TypeSafe AI or any model provider.

**Brian Doutey**, independent researcher, Limerick, Ireland
