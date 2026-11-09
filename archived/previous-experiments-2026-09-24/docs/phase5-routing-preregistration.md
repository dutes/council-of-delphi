# Phase 5: prospective routing comparison (v1)

Status: protocol written before any Phase 5 model or JEV calls. The Phase 3R
retrospective results informed this design and must be reported as exploratory
motivation, not as part of the new confirmatory sample.

## Research question

Does a paid, structured JEV judgment route second-round council deliberation
materially better than the deterministic rule “escalate if the three normalized
initial answers disagree”? The stronger individual council member remains a
separate benchmark; a council need not outperform it for this routing comparison
to be valid, but that limitation must be reported.

## Sample and freeze

- 500 unique, objectively scored public benchmark questions; one run each.
- Source totals match Phase 3R: MMLU-Pro 250, BBEH Mini 100, GSM1K 100,
  ARC-Challenge 50. MMLU categories are stratified. BBEH task strata cannot
  match Phase 3R exactly because only 138 unused Mini rows remain; it is
  sampled by fixed hash rank and the category-composition difference is a
  limitation.
- Pinned upstream revisions and fixed seed 20260926. Exclude every source row
  and exact question text in pilot, challenge, Phases 2/3/3R, and the unused
  Phase 4 robustness set. The generated JSONL and manifest are hashed before
  live calls. “Fresh” means not previously used in this project's live model
  experiments; no claim is made about model pretraining contamination.
- The original Phase 3R model IDs, temperature 0, Gemini LOW thinking,
  structured answer schema, source-aware scoring, choice-label transport,
  council size 3, JEV model, JEV payload allowlist, and deterministic routing
  threshold 0.10 are inherited unchanged. Their frozen hash is checked.
- The new own-answer-only reconsideration prompt and the new runner/analysis
  implementation are separately hashed in `configs/phase5_routing_v1.json`.
  Changes after the first live call require a new freeze and a new sample.

## Paired procedure

For each question, one independent round-one call is made to each of the
OpenAI, Anthropic, and Google members concurrently. No member sees another's
round-one output. JEV sees only the question, options, and anonymized council
state, never the ground truth, source metadata, or provider identities.

Before any second-round result is observed, record two routes:

1. JEV: escalate for weak/none agreement or deliberation score >= 0.10.
2. Simple: escalate whenever normalized round-one answers disagree.

If either route escalates, generate both of these branches from the same saved
round-one outputs:

- Peer reconsideration: the original Phase 3R disagreement-summary prompt,
  including the permission to retain one's initial answer.
- Own-answer reconsideration: each member sees only its own previous answer
  and reasoning, and is told it may retain the answer. No peer answer,
  distribution, JEV assessment, or ground truth is shown.

The branches are independent API calls. Both routing policies use the *same*
peer-round outputs when they escalate; if a policy stops, it uses the same
round-one majority vote. The own-answer branch supplies a secondary control
for revision without peer exposure. There is no generative judge or tie-resolving
model. All votes use the existing deterministic normalization/confidence/lexical
tie-break rule. Raw responses, usage, retries, failures, and branch membership
are retained in a separate SQLite database. Peer and own-answer branch order is
counterbalanced per question by a fixed-seed SHA-256 bit; the order is recorded
by the call sequence in SQLite.

## Predeclared outcomes and inference

Primary estimand: mean paired accuracy difference, **simple rule minus JEV
rule**, over the 500 unique questions. The practical noninferiority margin is
2 percentage points: declare the simple rule noninferior only if the lower end
of the question-level percentile bootstrap 95% interval exceeds -2 pp. Use
10,000 draws and fixed analysis seed 20260926. Also report the point estimate,
both CI bounds, paired right/wrong transitions, and conservative worst/best
missingness bounds. This is a test of a practically chosen margin, not proof
of exact equivalence. If the interval crosses the margin, the result is
inconclusive. A positive JEV or simple point estimate alone is not a
superiority claim.

Secondary/descriptive outcomes: initial majority and Google-member accuracy;
JEV and simple route escalation counts; accuracy under own-answer revision;
peer-vs-own revision transitions; source breakdown; recorded provider/JEV
token costs and latency. The own-answer comparisons are exploratory and not
covered by the primary noninferiority criterion. JEV cost is estimated at
$0.042 per million input tokens and zero output charge, as displayed by the
user's September 2026 usage screen; billed amounts may differ. Route-specific
cost excludes the own-answer control, while actual study spend includes it.

## Missingness, stopping, and operational controls

- All 500 questions are selected before live calls. No outcome-based interim
  stopping, source substitution, threshold tuning, or question redraw is
  permitted. A `--limit` run is a connectivity/operations check only; the
  full frozen sample remains registered.
- At most two recorded attempts per missing agent/stage. Successful calls are
  retained and not silently rerun on resume. A failed JEV request leaves that
  question incomplete; the simple rule cannot silently take over.
- Credit/quota exhaustion and the operator's recorded-cost cap pause calls.
  The cap is not a guaranteed invoice ceiling because failed provider calls
  may incur unreported charges. Resuming does not change the protocol.
- A complete paired question requires all three initial answers, JEV judgment,
  and, where either policy escalates, all three peer and all three own-answer
  revisions. No outcome is imputed from a partial council.
- If more than 2% of questions remain incomplete after allowed retries, the
  primary result is labeled not evaluable. At or below 2%, report complete-case
  estimates and worst/best-case missingness bounds. No unregistered extra
  attempts or substitutions to improve the headline result.

## Interpretation boundaries

This isolates the value of JEV **routing** relative to disagreement routing
because both policies share the same initial council and, when applicable,
the same peer-reconsideration outputs. It does not establish that JEV is
universally useful, that all debate is useful, or that the council beats its
strongest member. Hosted model behavior can drift even with pinned IDs and
temperature zero. The sample size is a cost-conscious fixed design, not a
guarantee of power for effects smaller than 2 percentage points; a wide
interval must be reported as inconclusive.
