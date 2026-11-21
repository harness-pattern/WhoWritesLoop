#!/usr/bin/env python3
"""Compute human-review agreement against the rule engine.

Usage:
  python3 compute_agreement.py --form review_form_filled.csv \
      --sample review_sample.csv --counts repo_counts.csv

Reads the filled audit form (one row per sampled PR), compares the reviewer's
final labels with the rule labels, and writes agreement_report.md.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def kappa(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x not in ("", None) and y not in ("", None)]
    n = len(pairs)
    if n == 0:
        return float("nan"), 0
    po = sum(x == y for x, y in pairs) / n
    ca = Counter(x for x, _ in pairs)
    cb = Counter(y for _, y in pairs)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in set(ca) | set(cb))
    k = (po - pe) / (1 - pe) if pe < 1 else 1.0
    return k, n


def final_label(row, dim):
    ok = (row.get(f"{dim}_correct") or "").strip().upper()
    if ok == "Y":
        return row.get(f"{dim}_rule", "")
    if ok == "N":
        return (row.get(f"{dim}_corrected") or "").strip()
    return ""


def pct(x):
    return f"{100*x:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--form", default=str(HERE / "review_form_filled.csv"))
    ap.add_argument("--sample", default=str(HERE / "review_sample.csv"))
    ap.add_argument("--counts", default=str(HERE / "repo_counts.csv"))
    ap.add_argument("--out", default=str(HERE / "agreement_report.md"))
    args = ap.parse_args()

    sample = {r["id"]: r for r in read_csv(args.sample)}
    form = [r for r in read_csv(args.form) if (r.get("id") or "").strip()]
    merged = []
    for r in form:
        s = sample.get(r["id"])
        if not s:
            continue
        row = dict(r)
        row["tier_rule"] = s["tier_rule"]
        row["layer_rule"] = s["primary_layer_rule"]
        row["change_type_rule"] = s["change_type_rule"]
        merged.append(row)

    lines = ["# Human review — agreement report", ""]
    lines.append(f"Reviewed records: **{len(merged)}** of {len(sample)} sampled.")
    lines.append("")

    id_title = [r for r in merged if r.get("title_matches")]
    id_merge = [r for r in merged if r.get("merge_status_matches")]
    if merged:
        lines.append(f"Identity: title match **{pct(sum(r.get('title_matches','').upper()=='Y' for r in merged)/len(merged))}**, "
                     f"merge-status match **{pct(sum(r.get('merge_status_matches','').upper()=='Y' for r in merged)/len(merged))}**.")
    lines.append("")

    dims = [
        ("tier", "Tier (T1/T2/T3)"),
        ("layer", "Primary architecture layer"),
        ("change_type", "Change type"),
    ]
    lines.append("| Dimension | n | Accuracy | Cohen's κ | Rule errors |")
    lines.append("|---|---:|---:|---:|---:|")
    summary = {}
    for dim, label in dims:
        rule, human = [], []
        for r in merged:
            h = final_label(r, dim)
            if not h:
                continue
            rule.append(r[f"{dim}_rule"])
            human.append(h)
        k, n = kappa(rule, human)
        acc = sum(x == y for x, y in zip(rule, human)) / n if n else float("nan")
        errors = sum(x != y for x, y in zip(rule, human))
        summary[dim] = {"n": n, "accuracy": acc, "kappa": k, "errors": errors}
        lines.append(f"| {label} | {n} | {pct(acc) if n else '—'} | {k:.3f} | {errors} |")
    lines.append("")

    # error breakdown: rule -> human
    for dim, label in dims:
        pairs = []
        for r in merged:
            h = final_label(r, dim)
            if h:
                pairs.append((r[f"{dim}_rule"], h))
        wrong = Counter((a, b) for a, b in pairs if a != b)
        if wrong:
            lines.append(f"**{label} — most common corrections**")
            lines.append("")
            lines.append("| rule | reviewer | count |")
            lines.append("|---|---|---:|")
            for (a, b), c in wrong.most_common(8):
                lines.append(f"| {a} | {b} | {c} |")
            lines.append("")

    conf = [int(r["confidence_1_5"]) for r in merged if str(r.get("confidence_1_5", "")).strip().isdigit()]
    if conf:
        lines.append(f"Mean reviewer confidence: **{sum(conf)/len(conf):.2f} / 5** (n={len(conf)}).")
        lines.append("")

    # repository counts
    counts_path = Path(args.counts)
    if counts_path.exists():
        rows = read_csv(counts_path)
        checked = []
        for r in rows:
            obs = (r.get("observed_prs") or "").strip()
            if obs.isdigit():
                checked.append((r["repo"], int(r["expected_prs"]), int(obs)))
        if checked:
            lines.append("## Repository-level count check")
            lines.append("")
            lines.append("| repository | expected | observed | difference | deviation |")
            lines.append("|---|---:|---:|---:|---:|")
            bad = 0
            for repo, exp, obs in checked:
                diff = obs - exp
                dev = abs(diff) / exp if exp else 0
                if dev > 0.01:
                    bad += 1
                lines.append(f"| {repo} | {exp:,} | {obs:,} | {diff:+,} | {pct(dev)} |")
            lines.append("")
            lines.append(f"Repositories exceeding 1% deviation: **{bad} / {len(checked)}**.")
            lines.append("")

    lines.append("## Acceptance")
    lines.append("")
    lines.append("| Check | Threshold | Observed | Verdict |")
    lines.append("|---|---|---|---|")
    for dim, label in dims:
        s = summary.get(dim, {})
        thresh = {"tier": 0.80, "layer": 0.65, "change_type": 0.60}[dim]
        k = s.get("kappa", float("nan"))
        verdict = "pass" if k >= thresh else "review required"
        lines.append(f"| {label} κ | ≥ {thresh:.2f} | {k:.3f} | {verdict} |")
    lines.append("")
    lines.append("If a dimension fails, inspect the correction table above, revise the codebook or the rule, and re-run the audit on a fresh sample. Do not tune the rule against the same 120 records and then report the tuned κ as independent.")
    lines.append("")

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    (HERE / "agreement_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
