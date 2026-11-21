#!/usr/bin/env python3
"""GitHub data collection for evolution2watch.

Subcommands:
  repos    -- resolve repo ids/archived status
  list     -- paginate PR list (census metadata) for each repo
  sample   -- pick stratified PR sample for detail fetch
  details  -- GraphQL batch fetch files/commits/reviews for sampled PRs
  status   -- print progress tables

Token is read from (in order): $GITHUB_TOKEN, <project>/.github_token
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "pipeline" / "config" / "repos.yaml"
API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"

EXCLUDE_TITLE = re.compile(
    r"^(chore\(deps\)|build\(deps\)|chore: release|release:? v?\d|v\d+\.\d+\.\d+$)",
    re.I,
)


def load_config():
    with open(CONFIG) as f:
        return yaml.safe_load(f)


def get_token() -> str:
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if not tok:
        for name in (".github_token", "github_token.txt", "token.txt", ".env"):
            p = ROOT / name
            if p.exists():
                raw = p.read_text().strip()
                if name == ".env":
                    m = re.search(r"(?m)^\s*(?:GITHUB_TOKEN|GH_TOKEN)\s*=\s*(.+)$", raw)
                    raw = m.group(1).strip() if m else ""
                tok = raw.strip().strip('"').strip("'")
                if tok.lower().startswith("bearer "):
                    tok = tok[7:].strip()
                if tok:
                    break
    if not tok:
        sys.exit(
            "ERROR: no GitHub token. Save a PAT as a single line in "
            f"{ROOT / 'github_token.txt'} (or .github_token), or set $GITHUB_TOKEN."
        )
    return tok


class Client:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "evolution2watch-research",
            }
        )

    def _throttle(self, r: requests.Response):
        remaining = int(r.headers.get("X-RateLimit-Remaining", "1"))
        reset = int(r.headers.get("X-RateLimit-Reset", "0"))
        if remaining < 50:
            wait = max(5, reset - int(time.time()) + 5)
            if wait > 5:
                print(f"  [rate] remaining={remaining}, sleeping {wait}s", flush=True)
                time.sleep(wait)

    def get(self, url, params=None, tries=5):
        for attempt in range(tries):
            r = self.s.get(url, params=params, timeout=60)
            if r.status_code == 200:
                self._throttle(r)
                return r.json(), r
            if r.status_code in (403, 429) or r.status_code >= 500:
                reset = int(r.headers.get("X-RateLimit-Reset", "0"))
                wait = max(10, reset - int(time.time()) + 5)
                wait = min(wait, 3600)
                print(f"  [http {r.status_code}] sleep {wait}s ({attempt+1}/{tries})", flush=True)
                time.sleep(wait)
                continue
            raise RuntimeError(f"GET {url} -> {r.status_code}: {r.text[:300]}")
        raise RuntimeError(f"GET {url} failed after {tries} tries")

    def graphql(self, query, variables=None, tries=5):
        for attempt in range(tries):
            try:
                r = self.s.post(GRAPHQL, json={"query": query, "variables": variables or {}}, timeout=180)
            except Exception as e:
                print(f"  [graphql {type(e).__name__}] retry {attempt+1}/{tries}", flush=True)
                time.sleep(10 * (attempt + 1))
                continue
            if r.status_code == 200:
                data = r.json()
                if "errors" in data and data["errors"]:
                    # partial data still usable
                    if not data.get("data"):
                        raise RuntimeError(f"GraphQL errors: {data['errors'][:2]}")
                self._throttle(r)
                return data
            reset = int(r.headers.get("X-RateLimit-Reset", "0"))
            wait = max(10, reset - int(time.time()) + 5) if reset else 60
            print(f"  [graphql {r.status_code}] sleep {wait}s", flush=True)
            time.sleep(min(wait, 3600))
        raise RuntimeError("graphql failed")


# ---------------------------------------------------------------- repos
def cmd_repos(cli: Client, cfg):
    con = db.connect()
    for r in cfg["repos"]:
        data, _ = cli.get(f"{API}/repos/{r['slug']}")
        con.execute(
            """INSERT INTO repos(repo_id, slug, category, language, archived_at, fetched_at)
               VALUES(?,?,?,?,?,datetime('now'))
               ON CONFLICT(repo_id) DO UPDATE SET
                 slug=excluded.slug, category=excluded.category,
                 language=excluded.language, archived_at=excluded.archived_at,
                 fetched_at=excluded.fetched_at""",
            (data["id"], data["full_name"], r["category"], r.get("language"), r.get("archived_at")),
        )
        con.commit()
        print(f"repo {data['id']:>10}  {data['full_name']:<32} archived={data['archived']} "
              f"stars={data['stargazers_count']}")


# ---------------------------------------------------------------- list
def cmd_list(cli: Client, cfg, only=None, max_pages=10**9):
    con = db.connect()
    start = datetime.fromisoformat(cfg["window"]["start"]).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(cfg["window"]["end"]).replace(tzinfo=timezone.utc)
    exclude_bots = {b.lower() for b in cfg["exclude_bots"]}

    for r in cfg["repos"]:
        if only and r["slug"] not in only:
            continue
        row = con.execute("SELECT repo_id FROM repos WHERE slug=?", (r["slug"],)).fetchone()
        if not row:
            print(f"! {r['slug']} not registered; run `repos` first")
            continue
        repo_id = row["repo_id"]
        if db.get_meta(con, f"list_done:{repo_id}") == "1":
            print(f"== {r['slug']}: already complete, skip")
            continue
        page = int(db.get_meta(con, f"list_page:{repo_id}", 1))
        inserted = excluded = 0
        done = False
        pages_this_run = 0
        while not done and page <= 400 and pages_this_run < max_pages:
            items, resp = cli.get(
                f"{API}/repos/{r['slug']}/pulls",
                {"state": "all", "sort": "created", "direction": "desc",
                 "per_page": 100, "page": page},
            )
            if not items:
                break
            for it in items:
                created = datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
                if created > end:
                    continue
                if created < start:
                    done = True
                    break
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
                if is_excluded:
                    excluded += 1
                else:
                    inserted += 1
            con.commit()
            pages_this_run += 1
            print(f"{r['slug']:<32} page {page:>3}  kept={inserted:>5} excluded={excluded:>4}", flush=True)
            page += 1
            db.set_meta(con, f"list_page:{repo_id}", page)
            time.sleep(0.25)

        if done or page > 400:
            db.set_meta(con, f"list_done:{repo_id}", 1)

        n = con.execute(
            "SELECT COUNT(*) c FROM prs WHERE repo_id=? AND detail_status!=3", (repo_id,)
        ).fetchone()["c"]
        con.execute("UPDATE repos SET pr_count=? WHERE repo_id=?", (n, repo_id))
        con.commit()
        print(f"== {r['slug']}: {n} PRs in window ({excluded} excluded)\n", flush=True)


# ---------------------------------------------------------------- sample
def cmd_sample(cli, cfg, total: int, per_repo_min: int):
    con = db.connect()
    random.seed(20261121)
    rows = con.execute(
        "SELECT repo_id, COUNT(*) c FROM prs WHERE detail_status=0 GROUP BY repo_id"
    ).fetchall()
    counts = {r["repo_id"]: r["c"] for r in rows}
    all_n = sum(counts.values())
    if all_n == 0:
        sys.exit("no PRs to sample; run `list` first")

    plan = {}
    for repo_id, c in counts.items():
        quota = max(per_repo_min, round(total * c / all_n))
        plan[repo_id] = min(quota, c)

    picked = []
    for repo_id, quota in plan.items():
        bot_cap = max(20, int(quota * 0.4))
        bots = con.execute(
            """SELECT number FROM prs WHERE repo_id=? AND detail_status=0
               AND author_type='Bot' ORDER BY RANDOM() LIMIT ?""",
            (repo_id, bot_cap),
        ).fetchall()
        take_bots = [b["number"] for b in bots]
        remain = quota - len(take_bots)
        humans = con.execute(
            """SELECT number FROM prs WHERE repo_id=? AND detail_status=0
               AND author_type!='Bot' ORDER BY RANDOM() LIMIT ?""",
            (repo_id, max(0, remain)),
        ).fetchall()
        picked += [(repo_id, n) for n in take_bots] + [(repo_id, h["number"]) for h in humans]
        print(f"repo {repo_id}: quota={quota} bots={len(take_bots)} humans={len(humans)}")

    with open(ROOT / "data" / "sample_plan.json", "w") as f:
        json.dump([{"repo_id": a, "number": b} for a, b in picked], f)
    print(f"\nselected {len(picked)} PRs -> data/sample_plan.json")


# ---------------------------------------------------------------- details
PR_FIELDS = """
  number title body
  author { login __typename }
  createdAt mergedAt closedAt state isDraft
  additions deletions changedFiles
  baseRefName headRefName
  mergeCommit { oid }
  comments { totalCount }
  reviews { totalCount }
  commits(first: 20) { totalCount nodes { commit { oid message committedDate author { name email user { login } } } } }
  files(first: 50) { nodes { path additions deletions changeType } }
"""


def build_query(numbers):
    parts = []
    for i, n in enumerate(numbers):
        parts.append(f"p{i}: pullRequest(number: {n}) {{ {PR_FIELDS} }}")
    return "query($owner:String!,$name:String!){ repository(owner:$owner,name:$name){ " + " ".join(parts) + " } }"


def cmd_details(cli: Client, cfg, limit: int, batch: int):
    con = db.connect()
    plan_path = ROOT / "data" / "sample_plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
    else:
        plan = [
            dict(r) for r in con.execute(
                "SELECT repo_id, number FROM prs WHERE detail_status=0 ORDER BY RANDOM() LIMIT ?",
                (limit,),
            ).fetchall()
        ]
    by_repo = {}
    for p in plan:
        by_repo.setdefault(p["repo_id"], []).append(p["number"])

    slug_by_id = {r["repo_id"]: r["slug"] for r in con.execute("SELECT repo_id,slug FROM repos")}
    done_total = 0
    t0 = time.time()
    for repo_id, numbers in by_repo.items():
        slug = slug_by_id[repo_id]
        owner, name = slug.split("/")
        pending = [
            n for n in numbers
            if con.execute(
                "SELECT detail_status FROM prs WHERE repo_id=? AND number=?", (repo_id, n)
            ).fetchone()["detail_status"] == 0
        ]
        for i in range(0, len(pending), batch):
            chunk = pending[i:i + batch]
            data = cli.graphql(build_query(chunk), {"owner": owner, "name": name})
            repo = (data.get("data") or {}).get("repository") or {}
            for j, n in enumerate(chunk):
                pr = repo.get(f"p{j}")
                if not pr:
                    con.execute(
                        "UPDATE prs SET detail_status=2, detail_error='null response' WHERE repo_id=? AND number=?",
                        (repo_id, n),
                    )
                    continue
                save_pr_detail(con, repo_id, n, pr)
                done_total += 1
            con.commit()
            rate = done_total / max(1, (time.time() - t0) / 60)
            print(f"{slug:<30} {i + len(chunk):>5}/{len(pending):<5} "
                  f"total={done_total} {rate:.0f}/min", flush=True)
            time.sleep(0.5)
    print(f"done: {done_total} PRs in {(time.time()-t0)/60:.1f} min")


def save_pr_detail(con, repo_id, number, pr):
    author = pr.get("author") or {}
    con.execute(
        """UPDATE prs SET title=?, body=?, author_login=?, author_type=?,
             closed_at=?, merged_at=?, state=?, is_draft=?, additions=?, deletions=?,
             changed_files=?, base_ref=?, head_ref=?, merge_commit_sha=?,
             review_comments=COALESCE(?, review_comments),
             commits_count=?, detail_status=1, detail_error=NULL
           WHERE repo_id=? AND number=?""",
        (
            pr.get("title"), (pr.get("body") or "")[:20000],
            author.get("login"), "Bot" if author.get("__typename") == "Bot" else "User",
            pr.get("closedAt"), pr.get("mergedAt"), pr.get("state"),
            1 if pr.get("isDraft") else 0,
            pr.get("additions"), pr.get("deletions"), pr.get("changedFiles"),
            pr.get("baseRefName"), pr.get("headRefName"),
            (pr.get("mergeCommit") or {}).get("oid"),
            ((pr.get("reviews") or {}).get("totalCount")),
            ((pr.get("commits") or {}).get("totalCount")),
            repo_id, number,
        ),
    )
    for f in ((pr.get("files") or {}).get("nodes") or []):
        con.execute(
            """INSERT INTO pr_files(repo_id, number, path, previous_path, status, additions, deletions)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(repo_id, number, path) DO UPDATE SET
                 additions=excluded.additions, deletions=excluded.deletions, status=excluded.status""",
            (repo_id, number, f["path"], f.get("previousPath"), f.get("changeType"),
             f.get("additions", 0), f.get("deletions", 0)),
        )
    for c in ((pr.get("commits") or {}).get("nodes") or []):
        cm = c.get("commit") or {}
        a = cm.get("author") or {}
        con.execute(
            """INSERT OR REPLACE INTO pr_commits(repo_id, number, sha, author_login,
                 author_name, author_email, message, committed_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (repo_id, number, cm.get("oid"), (a.get("user") or {}).get("login"),
             a.get("name"), a.get("email"), (cm.get("message") or "")[:8000],
             cm.get("committedDate")),
        )
    for rv in ((pr.get("reviews") or {}).get("nodes") or []):
        con.execute(
            """INSERT OR REPLACE INTO pr_reviews(repo_id, number, review_id, reviewer, state, submitted_at)
               VALUES(?,?,?,?,?,?)""",
            (repo_id, number, rv.get("id"), (rv.get("author") or {}).get("login"),
             rv.get("state"), rv.get("submittedAt")),
        )


# ---------------------------------------------------------------- status
def cmd_status(cli, cfg):
    con = db.connect()
    print(f"{'repo':<32}{'PRs':>7}{'detail':>8}{'pend':>7}{'excl':>7}")
    for r in con.execute("SELECT repo_id, slug FROM repos ORDER BY slug"):
        rid = r["repo_id"]
        n = con.execute("SELECT COUNT(*) c FROM prs WHERE repo_id=?", (rid,)).fetchone()["c"]
        d = con.execute("SELECT COUNT(*) c FROM prs WHERE repo_id=? AND detail_status=1", (rid,)).fetchone()["c"]
        p = con.execute("SELECT COUNT(*) c FROM prs WHERE repo_id=? AND detail_status=0", (rid,)).fetchone()["c"]
        e = con.execute("SELECT COUNT(*) c FROM prs WHERE repo_id=? AND detail_status=3", (rid,)).fetchone()["c"]
        print(f"{r['slug']:<32}{n:>7}{d:>8}{p:>7}{e:>7}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("repos")
    sp = sub.add_parser("list")
    sp.add_argument("--repo", action="append", default=None)
    sp.add_argument("--max-pages", type=int, default=10**9)
    sp = sub.add_parser("sample")
    sp.add_argument("--total", type=int, default=6000)
    sp.add_argument("--per-repo-min", type=int, default=150)
    sp = sub.add_parser("details")
    sp.add_argument("--limit", type=int, default=6000)
    sp.add_argument("--batch", type=int, default=20)
    sub.add_parser("status")
    args = ap.parse_args()

    cfg = load_config()
    cli = Client(get_token())
    if args.cmd == "repos":
        cmd_repos(cli, cfg)
    elif args.cmd == "list":
        cmd_list(cli, cfg, args.repo, args.max_pages)
    elif args.cmd == "sample":
        cmd_sample(cli, cfg, args.total, args.per_repo_min)
    elif args.cmd == "details":
        cmd_details(cli, cfg, args.limit, args.batch)
    elif args.cmd == "status":
        cmd_status(cli, cfg)


if __name__ == "__main__":
    main()
