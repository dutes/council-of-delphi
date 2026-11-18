"""Freeze the follow-up study. Run once, after calibration and a passing preflight.

    python tools/freeze_followup.py --cost-cap 60

Fills the matched council from results/followup-calibration.json, records the
dataset and implementation hashes in config/followup_v1.json, completes the
freeze record in docs/FOLLOWUP_PROTOCOL.md, and marks the study frozen. After
this, run_followup.py and analyze_followup.py refuse to run if any frozen file
changes. Commit the result before the first scored call.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from followup_study.spec import PROVIDERS, implementation_hash, load_questions, sha256_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config/followup_v1.json")
    parser.add_argument("--calibration", default="results/followup-calibration.json")
    parser.add_argument("--protocol", default="docs/FOLLOWUP_PROTOCOL.md")
    parser.add_argument("--cost-cap", type=float, required=True, help="recorded-cost cap in USD")
    args = parser.parse_args()

    config_path = ROOT / args.config
    spec = json.loads(config_path.read_text(encoding="utf-8"))
    if spec.get("status") == "frozen":
        raise SystemExit("Already frozen. A frozen study is never re-frozen; write an amendment instead.")
    calibration = json.loads((ROOT / args.calibration).read_text(encoding="utf-8"))

    calibration_sha = sha256_file(ROOT / spec["calibration_path"])
    if calibration["calibration_sha256"] != calibration_sha:
        raise SystemExit("The calibration results were produced from a different calibration set")
    load_questions(ROOT / spec["dataset_path"], expected_count=spec["question_count"])
    dataset_sha = sha256_file(ROOT / spec["dataset_path"])
    manifest = json.loads((ROOT / "data/followup.manifest.json").read_text(encoding="utf-8"))
    if manifest["main"]["sha256"] != dataset_sha or manifest["calibration"]["sha256"] != calibration_sha:
        raise SystemExit("Dataset files don't match data/followup.manifest.json")

    prices = {e["model"]: e["pricing"] for p in PROVIDERS for e in spec["candidates"][p]}
    for provider in PROVIDERS:
        model = calibration["chosen"][provider]["model"]
        spec["arms"]["matched"][provider] = model
        spec["pricing"][model] = prices[model]
    today = dt.date.today().isoformat()
    spec.update({
        "dataset_sha256": dataset_sha, "calibration_sha256": calibration_sha,
        "max_recorded_cost_usd": args.cost_cap, "calibration": {
            "jev_alone_accuracy": calibration["jev_alone_accuracy"],
            "chosen": calibration["chosen"], "spend_usd": calibration["calibration_spend_usd"]},
    })

    # Complete the freeze record before hashing, so the protocol that's hashed is the final one.
    protocol_path = ROOT / args.protocol
    protocol = protocol_path.read_text(encoding="utf-8")
    head, marker, _ = protocol.partition("## Freeze record")
    if not marker:
        raise SystemExit("Couldn't find the freeze record section in the protocol")
    jev_pct = 100 * calibration["jev_alone_accuracy"]
    picks = "\n".join(
        f"  - {p}: `{c['model']}`, {100 * c['accuracy']:.1f}% on calibration "
        f"({abs(c['gap_to_jev_pp']):.1f} points {'below' if c['gap_to_jev_pp'] >= 0 else 'above'} JEV alone), {c['rule']}"
        for p, c in calibration["chosen"].items())
    candidates = "\n".join(f"  - {p}: " + ", ".join(f"`{e['model']}`" for e in spec["candidates"][p])
                           for p in PROVIDERS)
    record = (
        "## Freeze record\n\n"
        f"- Date: {today}\n"
        f"- Council candidate list:\n{candidates}\n"
        f"- Calibration: JEV alone scored {jev_pct:.1f}% on the 60 calibration questions. Chosen matched council:\n"
        f"{picks}\n"
        f"- Cost cap: ${args.cost_cap:.2f}\n"
        f"- Seeds: crowd {spec['crowd_seed']}, arbitration {spec['arbitration_seed']}, "
        f"tie {spec['tie_seed']}, analysis {spec['analysis_seed']}\n"
        f"- Dataset SHA-256: main `{dataset_sha}`, calibration `{calibration_sha}`\n"
        "- Implementation SHA-256 (covers this file): recorded in `config/followup_v1.json`\n"
    )
    protocol = head + record
    status_start = protocol.index("Status:")
    status_end = protocol.index("\n\n", status_start)
    protocol = (protocol[:status_start]
                + f"Status: **Frozen on {today}**, before any scored call. Changes after this date are\n"
                  "amendments, recorded in this file with their date and reason."
                + protocol[status_end:])
    protocol_path.write_text(protocol, encoding="utf-8", newline="\n")

    spec["implementation_sha256"] = implementation_hash(ROOT)
    spec["status"] = "frozen"
    spec["frozen_on"] = today
    config_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Frozen on {today}.")
    print(f"Implementation SHA-256: {spec['implementation_sha256']}")
    print(f"Config SHA-256: {sha256_file(config_path)}")
    print("Commit and push now, before the first scored call.")


if __name__ == "__main__":
    main()
