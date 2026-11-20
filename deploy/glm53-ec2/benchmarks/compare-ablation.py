#!/usr/bin/env python3
"""Compare independently measured baseline/concise/MTP JSONL files.

Use only complete measurements; never mix warmups or historical baselines.
The answer-review file supports manual review, not automated correctness claims.
"""
import argparse
import json
import pathlib
import statistics


def quantile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    lo = int(position)
    return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (position - lo)


def describe(values):
    return dict(n=len(values), mean=statistics.mean(values),
                p50=quantile(values, .5), p95=quantile(values, .95))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=pathlib.Path)
    args = parser.parse_args()
    data = {}
    batches = {}
    for variant in ("baseline", "concise", "mtp"):
        rows = [json.loads(line) for line in (args.directory / f"{variant}.jsonl").read_text().splitlines()]
        batches[variant] = [r for r in rows if r.get("type") == "summary"]
        measured = [r for r in rows if r.get("type") != "summary" and not r.get("warmup")]
        keys = [(r["case"], r["concurrency"], r["iteration"]) for r in measured]
        if len(keys) != len(set(keys)):
            raise ValueError(f"{variant}: duplicate measurement keys")
        if len(measured) != 40 or any(r.get("error") or "stop" not in r["finish_reasons"] or not r["answer"].strip() for r in measured):
            raise ValueError(f"{variant}: expected 40 complete, nontruncated answers")
        data[variant] = dict(zip(keys, measured))
    if any(set(rows) != set(data["baseline"]) for rows in data.values()):
        raise ValueError("Unpaired scenario/concurrency/iteration keys")
    metrics = {
        "ttft_s": lambda r: r["ttft_s"],
        "first_visible_s": lambda r: r["first_visible_s"],
        "ttot_s": lambda r: r["ttot_s"],
        "e2e_s": lambda r: r["e2e_s"],
        "approx_tpot_ms": lambda r: r["approx_tpot_s"] * 1000,
        "output_tokens": lambda r: r["usage"]["completion_tokens"],
        "reasoning_tokens": lambda r: r["usage"]["reasoning_tokens"],
        "nonreasoning_output_tokens": lambda r: r["usage"]["completion_tokens"] - r["usage"]["reasoning_tokens"],
        "input_tokens": lambda r: r["usage"]["prompt_tokens"],
        "answer_chars": lambda r: len(r["answer"]),
        "reasoning_chars": lambda r: r["reasoning_chars"],
    }
    groups = []
    for concurrency in (1, 2):
        for case in [None] + sorted({key[0] for key in data["baseline"]}):
            selected = [key for key in data["baseline"] if key[1] == concurrency and (case is None or key[0] == case)]
            group = dict(concurrency=concurrency, case=case or "all", variants={}, comparisons={})
            for variant, rows in data.items():
                group["variants"][variant] = {metric: describe([getter(rows[key]) for key in selected]) for metric, getter in metrics.items()}
            for variant in ("concise", "mtp"):
                # Ratios of means capture total token/time savings. Pairwise
                # differences remain available to show scenario variability.
                comparison = {}
                for metric, getter in metrics.items():
                    base = group["variants"]["baseline"][metric]["mean"]
                    treatment = group["variants"][variant][metric]["mean"]
                    comparison[metric] = {
                        "change_percent_of_baseline_mean": (treatment / base - 1) * 100 if base else None,
                        "paired_difference": describe([getter(data[variant][key]) - getter(data["baseline"][key]) for key in selected]),
                    }
                group["comparisons"][variant] = comparison
            groups.append(group)
    result = dict(groups=groups, batches=batches,
                  limitation="Descriptive small-sample sequential ablations; answer correctness requires independent review.")
    (args.directory / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    review = ["# Paired answer review\n", "Iteration 0 of every scenario/concurrency; proposals are not executed proofs.\n"]
    for key in sorted(data["baseline"]):
        if key[2] != 0:
            continue
        review.append(f"## {key[0]} / concurrency {key[1]}\n")
        for variant in data:
            row = data[variant][key]
            review.append(f"### {variant}\n\nOutput tokens: {row['usage']['completion_tokens']}; TTOT: {row['ttot_s']:.3f}s\n\n{row['answer']}\n")
    (args.directory / "paired-answers.md").write_text("\n".join(review))
    for group in groups:
        if group["case"] == "all":
            print(json.dumps(group))


if __name__ == "__main__":
    main()
