import argparse
import json
import os
import pandas as pd


def generate_report(runs_dir: str = "eval/runs"):
    files = [
        os.path.join(runs_dir, f)
        for f in os.listdir(runs_dir)
        if f.endswith(".jsonl")
    ] if os.path.exists(runs_dir) else []

    if not files:
        print("No evaluation run files found in", runs_dir)
        return

    records = []
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))

    if not records:
        print("No evaluation records found.")
        return

    df = pd.DataFrame(records)

    print("\n================ EVALUATION SUMMARY REPORT ================")
    summary = (
        df.groupby(["system"])
        .agg(
            total_items=("item_id", "count"),
            accuracy=("correct", "mean"),
            avg_confidence=("p", "mean"),
            escalated_count=("outcome", lambda x: (x == "escalated").sum()),
            fallback_count=("outcome", lambda x: (x == "fallback").sum()),
        )
        .reset_index()
    )

    print(summary.to_string(index=False))
    print("============================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render evaluation report")
    parser.add_argument("--runs-dir", default="eval/runs")
    args = parser.parse_args()

    generate_report(args.runs_dir)
