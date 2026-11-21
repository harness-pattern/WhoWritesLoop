#!/usr/bin/env python3
"""LLM-as-a-Judge harness: patch fetch, batch export, label ingest, kappa.

Subcommands:
  fetch-patches --n 300        # download .diff for sampled PRs (REST, 1 req/PR)
  export --n 300 --size 40     # write data/judge/batch_XX.jsonl
  ingest --file labels.jsonl   # write judge_json + judge_status=1
  kappa --truth adjudicated.csv --pred judge|rule
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import pandas as pd
import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
from fetch import Client, get_token, load_config, ROOT  # noqa: E402

PATCH_DIR = ROOT / "data" / "patches"
JUDGE_DIR = ROOT / "data" / "judge"
JUDGE_DIR.mkdir(parents=True, exist_ok=True)


def cmd_fetch_patches(n: int, seed: int):
    cfg = load_config()
    con = db.connect()
    random.seed(seed)
    rows = con.execute(
        """SELECT repo_id, number FROM prs WHERE detail_status=1 AND judge_status=0
           ORDER BY RANDOM() LIMIT ?""", (n,)
    ).fetchall()
    slugs = {r["repo_id"]: r["slug"] for r in con.execute("SELECT repo_id, slug FROM repos")}
    cli = Client(get_token())
    cli.s.headers["Accept"] = "application/vnd.github.v3.diff"
    for i, r in enumerate(rows, 1):
        out = PATCH_DIR / str(r["repo_id"]) / f"{r['number']}.diff"
        if out.exists():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://api.github.com/repos/{slugs[r['repo_id']]}/pulls/{r['number']}"
        for attempt in range(3):
            resp = cli.s.get(url, timeout=60)
            if resp.status_code == 200:
                out.write_text(resp.text[:120_000])
                break
            if resp.status_code in (403, 429):
                import time
                time.sleep(60)
                continue
            out.write_text("")
            break
        print(f"{i}/{len(rows)} {slugs[r['repo_id']]} #{r['number']} "
              f"{len(out.read_text()) if out.exists() else 0} bytes", flush=True)


def cmd_export(n: int, size: int, seed: int):
    con = db.connect()
    random.seed(seed)
    rows = con.execute(
        """SELECT p.*, r.slug FROM prs p JOIN repos r USING(repo_id)
           WHERE p.detail_status=1 AND p.judge_status=0 AND p.tier IS NOT NULL"""
    ).fetchall()
    patched = {(int(p.parent.name), int(p.stem)) for p in PATCH_DIR.glob("*/*.diff")}
    rows = [r for r in rows if (r["repo_id"], r["number"]) in patched]
    random.shuffle(rows)
    rows = rows[:n]
    batches = [rows[i:i + size] for i in range(0, len(rows), size)]
    for bi, batch in enumerate(batches, 1):
        path = JUDGE_DIR / f"batch_{bi:02d}.jsonl"
        with open(path, "w") as f:
            for r in batch:
                files = con.execute(
                    """SELECT path, status, additions, deletions, layer FROM pr_files
                       WHERE repo_id=? AND number=?
                       ORDER BY (additions+deletions) DESC LIMIT 20""",
                    (r["repo_id"], r["number"]),
                ).fetchall()
                commits = con.execute(
                    "SELECT message FROM pr_commits WHERE repo_id=? AND number=? LIMIT 12",
                    (r["repo_id"], r["number"]),
                ).fetchall()
                patch_path = PATCH_DIR / str(r["repo_id"]) / f"{r['number']}.diff"
                if not patch_path.exists():
                    continue
                patch = patch_path.read_text()[:2500]
                item = {
                    "id": f"{r['repo_id']}:{r['number']}",
                    "repo": r["slug"], "number": r["number"], "tier_rule": r["tier"],
                    "title": r["title"], "body": (r["body"] or "")[:800],
                    "files": [dict(f) for f in files],
                    "commits": [c["message"][:300] for c in commits],
                    "patch_excerpt": patch,
                    "rule_layers": json.loads(r["layers"]) if r["layers"] else {},
                    "rule_change_type": r["change_type"],
                }
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"{path} ({len(batch)} items)")
    print("Now label each batch with the schema in docs/03_labeling_spec.md §2.3.")


def cmd_ingest(path: str):
    con = db.connect()
    n = 0
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        rid, num = obj["id"].split(":")
        con.execute(
            "UPDATE prs SET judge_json=?, judge_status=1, abstraction_label=? WHERE repo_id=? AND number=?",
            (json.dumps(obj, ensure_ascii=False), obj.get("abstraction_vs_patch"), int(rid), int(num)),
        )
        n += 1
    con.commit()
    print(f"ingested {n} labels")


def kappa(a, b):
    a, b = list(a), list(b)
    n = len(a)
    if n == 0:
        return float("nan")
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def cmd_kappa(truth_path: str, pred: str):
    con = db.connect()
    t = pd.read_csv(truth_path)
    rows = []
    for _, r in t.iterrows():
        rid, num = int(r["repo_id"]), int(r["number"])
        row = con.execute("SELECT * FROM prs WHERE repo_id=? AND number=?", (rid, num)).fetchone()
        if not row:
            continue
        if pred == "rule":
            p_tier, p_ct = row["tier"], row["change_type"]
            p_layers = set(json.loads(row["layers"] or "{}").keys())
        else:
            j = json.loads(row["judge_json"] or "{}")
            p_tier, p_ct = row["tier"], j.get("change_type")
            p_layers = set(j.get("layers") or [])
        rows.append({
            "tier_true": r["tier"], "tier_pred": p_tier,
            "ct_true": r.get("change_type"), "ct_pred": p_ct,
            "layers_true": set(str(r.get("layers", "")).split("|")) if pd.notna(r.get("layers")) else set(),
            "layers_pred": p_layers,
        })
    d = pd.DataFrame(rows)
    out = {"n": len(d)}
    if len(d):
        out["kappa_tier"] = kappa(d["tier_true"], d["tier_pred"])
        sub = d.dropna(subset=["ct_true"])
        if len(sub):
            out["kappa_change_type"] = kappa(sub["ct_true"], sub["ct_pred"])
        jac = [len(t & p) / len(t | p) if (t | p) else 1 for t, p in zip(d["layers_true"], d["layers_pred"])]
        out["mean_layer_jaccard"] = sum(jac) / len(jac)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fetch-patches"); p.add_argument("--n", type=int, default=300); p.add_argument("--seed", type=int, default=7)
    p = sub.add_parser("export"); p.add_argument("--n", type=int, default=300); p.add_argument("--size", type=int, default=40); p.add_argument("--seed", type=int, default=7)
    p = sub.add_parser("ingest"); p.add_argument("--file", required=True)
    p = sub.add_parser("kappa"); p.add_argument("--truth", required=True); p.add_argument("--pred", choices=["judge", "rule"], default="judge")
    args = ap.parse_args()
    if args.cmd == "fetch-patches":
        cmd_fetch_patches(args.n, args.seed)
    elif args.cmd == "export":
        cmd_export(args.n, args.size, args.seed)
    elif args.cmd == "ingest":
        cmd_ingest(args.file)
    elif args.cmd == "kappa":
        cmd_kappa(args.truth, args.pred)


if __name__ == "__main__":
    main()
