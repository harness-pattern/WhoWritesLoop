#!/usr/bin/env python3
"""Parallel PR-list fetcher (resumable, per-repo cursor).

The serial fetcher is latency-bound (~4-5 s/page from this sandbox).
This variant fetches blocks of pages concurrently and writes in page order.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import requests
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
from fetch import API, Client, EXCLUDE_TITLE, get_token, load_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--repo", action="append")
    ap.add_argument("--max-blocks", type=int, default=1000)
    args = ap.parse_args()

    cfg = load_config()
    only = set(args.repo) if args.repo else None
    start = datetime.fromisoformat(cfg["window"]["start"]).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(cfg["window"]["end"]).replace(tzinfo=timezone.utc)
    exclude_bots = {b.lower() for b in cfg["exclude_bots"]}
    cli = Client(get_token())
    con = db.connect()
    session = cli.s

    headers = dict(session.headers)

    def get_page(slug, page):
        for attempt in range(6):
            try:
                r = requests.get(
                    url=f"{API}/repos/{slug}/pulls",
                    params={"state": "all", "sort": "created", "direction": "desc",
                            "per_page": 100, "page": page},
                    headers=headers, timeout=90,
                )
                if r.status_code == 200:
                    return r.json()
                if r.status_code in (403, 429, 502, 503, 504):
                    print(f"  [http {r.status_code}] page {page} remaining={r.headers.get('X-RateLimit-Remaining')}", flush=True)
                    reset = int(r.headers.get("X-RateLimit-Reset", "0"))
                    wait = max(5, reset - int(time.time()) + 3) if reset else 20
                    time.sleep(min(wait, 120))
                    continue
                return None
            except Exception as e:
                if attempt == 5:
                    print(f"  [err] page {page}: {type(e).__name__}: {str(e)[:80]}", flush=True)
                time.sleep(5 * (attempt + 1))
        return None

    for r in cfg["repos"]:
        if only and r["slug"] not in only:
            continue
        row = con.execute("SELECT repo_id FROM repos WHERE slug=?", (r["slug"],)).fetchone()
        if not row:
            print(f"! {r['slug']} not registered")
            continue
        repo_id = row["repo_id"]
        if db.get_meta(con, f"list_done:{repo_id}") == "1":
            continue

        page = int(db.get_meta(con, f"list_page:{repo_id}", 1))
        done = False
        total = 0
        t0 = time.time()
        blocks = 0
        while not done and blocks < args.max_blocks:
            pages = list(range(page, page + args.workers))
            results = None
            for attempt in range(3):
                with ThreadPoolExecutor(max_workers=args.workers) as ex:
                    results = list(ex.map(lambda p: get_page(r["slug"], p), pages))
                if all(x is not None for x in results):
                    break
                print(f"  [retry] {r['slug']} pages {pages[0]}-{pages[-1]} had errors", flush=True)
                time.sleep(30)
            if results is None or any(x is None for x in results):
                print(f"  [abort] {r['slug']} at page {page}; will resume next run", flush=True)
                break
            for pg, items in zip(pages, results):
                if not items:
                    done = True
                    break
                for it in items:
                    created = datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
                    if created > end:
                        continue
                    if created < start:
                        done = True
                        continue
                    login = (it.get("user") or {}).get("login", "")
                    title = it.get("title") or ""
                    is_excluded = login.lower() in exclude_bots or bool(EXCLUDE_TITLE.match(title))
                    con.execute(
                        """INSERT INTO prs(repo_id, number, node_id, title, body, author_login,
                               author_type, author_association, created_at, closed_at, merged_at,
                               state, is_draft, base_ref, head_ref, comments_count, review_comments,
                               commits_count, labels, detail_status, tier)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(repo_id, number) DO UPDATE SET
                             title=excluded.title, body=excluded.body, state=excluded.state,
                             merged_at=excluded.merged_at, closed_at=excluded.closed_at""",
                        (
                            repo_id, it["number"], it.get("node_id"), title,
                            (it.get("body") or "")[:20000],
                            login, (it.get("user") or {}).get("type", "User"),
                            it.get("author_association"),
                            it["created_at"], it.get("closed_at"), it.get("merged_at"),
                            it["state"], 1 if it.get("draft") else 0,
                            (it.get("base") or {}).get("ref"), (it.get("head") or {}).get("ref"),
                            it.get("comments", 0), it.get("review_comments", 0),
                            it.get("commits", 0),
                            json.dumps([l["name"] for l in it.get("labels", [])]),
                            3 if is_excluded else 0,
                            "EXCLUDED" if is_excluded else None,
                        ),
                    )
                    total += 1
                if done:
                    break
            con.commit()
            page += args.workers
            blocks += 1
            db.set_meta(con, f"list_page:{repo_id}", page)
            n = con.execute("SELECT COUNT(*) c FROM prs WHERE repo_id=?", (repo_id,)).fetchone()["c"]
            print(f"{r['slug']:<32} page {page:>4}  rows={n:>6}  {total/(time.time()-t0):.0f} rows/s", flush=True)

        if done:
            db.set_meta(con, f"list_done:{repo_id}", 1)
        n = con.execute(
            "SELECT COUNT(*) c FROM prs WHERE repo_id=? AND detail_status!=3", (repo_id,)
        ).fetchone()["c"]
        con.execute("UPDATE repos SET pr_count=? WHERE repo_id=?", (n, repo_id))
        con.commit()
        print(f"== {r['slug']}: {n} PRs in window{' (DONE)' if done else ''}\n", flush=True)


if __name__ == "__main__":
    main()
