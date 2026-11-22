#!/usr/bin/env python3
"""Fetch GitHub .diff excerpts for the 120 review-package PRs.

Caches to data/review_patches/{repo_id}/{number}.diff, truncated to 24 KB.
Run once before generate.py; generate.py embeds the first ~7 KB per record.
"""
from __future__ import annotations

import csv
import sqlite3
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from fetch import get_token  # noqa: E402

CACHE = ROOT / "data" / "review_patches"
DB = ROOT / "data" / "evolution2watch_data.sqlite"


def main():
    rows = list(csv.DictReader(open(HERE / "review_sample.csv", encoding="utf-8")))
    con = sqlite3.connect(DB)
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": "evolution2watch-review",
    }
    todo = []
    for r in rows:
        rid = con.execute("SELECT repo_id FROM repos WHERE slug=?", (r["repo"],)).fetchone()[0]
        p = CACHE / str(rid) / f"{r['pr_number']}.diff"
        if not p.exists():
            todo.append((rid, r["repo"], int(r["pr_number"]), p))
    print(f"{len(todo)} patches to fetch ({len(rows)} review rows)")
    for i, (rid, slug, num, path) in enumerate(todo, 1):
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://api.github.com/repos/{slug}/pulls/{num}"
        for attempt in range(4):
            try:
                resp = requests.get(url, headers=headers, timeout=60)
                if resp.status_code == 200:
                    path.write_text(resp.text[:24000], encoding="utf-8")
                    break
                if resp.status_code in (403, 429):
                    time.sleep(20)
                    continue
                path.write_text("", encoding="utf-8")
                break
            except Exception as e:
                if attempt == 3:
                    print("  error", slug, num, e)
                time.sleep(3)
        print(f"{i}/{len(todo)} {slug} #{num} {path.stat().st_size if path.exists() else 0} B", flush=True)
        time.sleep(0.15)


if __name__ == "__main__":
    main()
