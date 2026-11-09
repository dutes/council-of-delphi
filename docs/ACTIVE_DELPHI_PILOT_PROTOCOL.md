# Engineering pilot: classifier-led iterative Delphi retrieval

Author: Brian Doutey, independent researcher (no institutional affiliation)

Status: frozen before API preflight or pilot calls. This 30-question pilot is
for engineering validation only and is excluded from any later confirmatory
analysis.

## Purpose

The prior evidence-partitioned experiment showed that one-round specialist
summaries can omit indispensable facts. This pilot tests whether JEV can remain
a classifier—not a conversational reasoning model—while controlling a fixed,
iterative evidence-retrieval protocol.

## Fixed controller

Every problem contains a novel three-link chain:

```text
artifact -> vault -> sector -> clearance code
```

One indispensable link is placed with each of three non-reasoning providers.
Link ownership rotates through all six provider permutations. Each provider
also receives five distractors.

The controller begins with the artifact and uses three fixed retrieval stages:

1. request the vault storing the named artifact;
2. request the sector administering the accepted vault;
3. request the clearance used by the accepted sector.

At every stage, all providers receive the same targeted request and their own
unchanged private partition. They return structured JSON and cite zero or more
evidence IDs. Valid cited IDs are resolved to the original evidence statements.
JEV receives the requested subject/relation, the accepted path, and the cited
candidate statements. It makes one closed-set classification:

- accept a named evidence item and advance;
- retry the same targeted retrieval once; or
- halt unresolved.

JEV neither writes follow-up questions nor generates an answer. The controller
constructs the next fixed request from the object in the evidence item that JEV
accepted. After the third link, the controller maps the accepted clearance to
the four answer choices. There are at most two retrieval attempts per stage.

## Models

- OpenAI `gpt-4.1-mini-2025-04-14`;
- Anthropic `claude-haiku-4-5-20251001`;
- Mistral `ministral-14b-2512` with reasoning disabled;
- JEV `jev-latest` for closed-set action classification.

## Pilot checks

The protocol is ready for a separately generated 300-question confirmatory
study only if all of these engineering gates pass:

- at least 29 of 30 questions produce a terminal outcome;
- at least 27 of 30 complete the full three-link path;
- at least 27 of 30 return the correct answer;
- no provider owns a given link position more than five times;
- at least 95% of accepted evidence IDs are valid citations returned by a
  specialist in that stage;
- hidden reasoning tokens/blocks are rejected as in the previous study.

These thresholds are feasibility checks, not inferential claims. Any prompt,
controller, model, retry, or parsing change after inspecting the pilot requires
a new confirmatory freeze and a disjoint dataset.

## Interpretation boundary

Success would establish that closed-set JEV classifications can route evidence
through a synthetic multi-round protocol. It would not establish performance
on uncontrolled documents, conflicting human testimony, or open-ended question
generation. The synthetic controller knows the relation schema but never uses
the hidden correct answer or support flags to select evidence.

## Independence and disclosure

This is Brian Doutey's personal project. No person or organization paid for,
commissioned, or influenced the work. The author reports no affiliation or
relationship with TypeSafe and no external funding.

