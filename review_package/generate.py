#!/usr/bin/env python3
"""Generate the human-review package for repository-mining verification.

Outputs (in this directory):
  review_sample.csv      120 stratified PRs with rule labels and GitHub URLs
  review_form.csv        blank audit form (one row per sampled PR)
  repo_counts.csv        expected per-repo PR counts + GitHub search links
  revert_sample.csv      15 revert-link cases
  pattern_sample.csv     15 pattern-hit cases
  review.html            self-contained review app (exports CSV)
  manifest.json          seed, counts, and SHA-256 of generated files
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB = ROOT / "data" / "evolution2watch_data.sqlite"
SEED = 20261121
N_PER_TIER = 40

LAYERS = ["L1", "L2", "L3", "L4", "L0", "LD", "UNCLASSIFIED"]
TIERS = ["T1", "T2", "T3"]


def primary_layer(s):
    try:
        d = json.loads(s or "{}")
    except Exception:
        return ""
    if not d:
        return ""
    return max(d, key=d.get)


def pick_stratified(rows, n):
    """Round-robin across repositories after shuffling within each repo."""
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["slug"], []).append(r)
    for v in by_repo.values():
        random.shuffle(v)
    out = []
    repos = sorted(by_repo)
    i = 0
    while len(out) < n and any(by_repo.values()):
        repo = repos[i % len(repos)]
        if by_repo[repo]:
            out.append(by_repo[repo].pop())
        i += 1
        if i > 10000:
            break
    return out


def main():
    random.seed(SEED)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    rows = con.execute(
        """SELECT p.repo_id, r.slug, r.category, p.number, p.title, p.body, p.author_login,
                  p.created_at, p.merged_at, p.state, p.tier, p.layers,
                  p.change_type, p.detail_status
           FROM prs p JOIN repos r USING(repo_id)
           WHERE p.detail_status=1 AND p.tier IN ('T1','T2','T3')
             AND p.layers IS NOT NULL AND p.layers NOT IN ('', '{}')"""
    ).fetchall()
    rows = [dict(r) for r in rows]
    rows = [r for r in rows if primary_layer(r["layers"]) not in ("", "UNCLASSIFIED")]

    for r in rows:
        r["_primary"] = primary_layer(r["layers"])

    # 20 rows per layer, with 7/7/6 tier balance inside each layer
    sample = []
    layer_order = ["L1", "L2", "L3", "L4", "L0", "LD"]
    for layer in layer_order:
        pool = [r for r in rows if r["_primary"] == layer]
        chosen, chosen_ids = [], set()
        for tier, target in (("T1", 7), ("T2", 7), ("T3", 6)):
            sub = [r for r in pool if r["tier"] == tier and id(r) not in chosen_ids]
            take = pick_stratified(sub, min(target, len(sub)))
            chosen += take
            chosen_ids |= {id(x) for x in take}
        if len(chosen) < 20:
            rest = [r for r in pool if id(r) not in chosen_ids]
            take = pick_stratified(rest, 20 - len(chosen))
            chosen += take
            chosen_ids |= {id(x) for x in take}
        sample += chosen[:20]
    random.shuffle(sample)

    sample_rows = []
    for i, r in enumerate(sample, 1):
        author = r["author_login"]
        if not author:
            ca = con.execute(
                "SELECT author_name FROM pr_commits WHERE repo_id=? AND number=? LIMIT 1",
                (r["repo_id"], r["number"]),
            ).fetchone()
            author = (ca["author_name"] if ca else "") or "unknown (deleted account)"
        sample_rows.append({
            "id": f"S{i:03d}",
            "repo": r["slug"],
            "pr_number": r["number"],
            "url": f"https://github.com/{r['slug']}/pull/{r['number']}",
            "title": (r["title"] or "").replace("\n", " ").strip(),
            "author_login": author,
            "created_at": (r["created_at"] or "")[:10],
            "merged_at": (r["merged_at"] or "")[:10],
            "merge_status": "merged" if r["merged_at"] else ("open" if str(r["state"]).lower() == "open" else "closed-unmerged"),
            "tier_rule": r["tier"],
            "primary_layer_rule": r["_primary"] or "UNCLASSIFIED",
            "layers_rule": ",".join(sorted(json.loads(r["layers"] or "{}").keys())),
            "change_type_rule": r["change_type"] or "",
            "body_excerpt": (r["body"] or "")[:1200],
            "files": [
                {"path": f["path"], "layer": f["layer"], "a": f["additions"], "d": f["deletions"]}
                for f in con.execute(
                    """SELECT path, layer, additions, deletions FROM pr_files
                       WHERE repo_id=? AND number=? ORDER BY (additions+deletions) DESC LIMIT 20""",
                    (r["repo_id"], r["number"]),
                )
            ],
            "commits": [
                (x["message"] or "").split("\n")[0][:180]
                for x in con.execute(
                    "SELECT message FROM pr_commits WHERE repo_id=? AND number=? LIMIT 8",
                    (r["repo_id"], r["number"]),
                )
            ],
        })

    with open(HERE / "review_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sample_rows[0]))
        w.writeheader()
        w.writerows(sample_rows)

    form_cols = [
        "id", "reviewer", "review_date",
        "title_matches", "merge_status_matches",
        "tier_correct", "tier_corrected",
        "layer_correct", "layer_corrected",
        "change_type_correct", "change_type_corrected",
        "confidence_1_5", "notes",
    ]
    with open(HERE / "review_form.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=form_cols)
        w.writeheader()
        for r in sample_rows:
            w.writerow({"id": r["id"]})

    # ---- repository-level count verification
    counts = con.execute(
        """SELECT r.slug, r.category, COUNT(*) n
           FROM prs p JOIN repos r USING(repo_id)
           WHERE p.detail_status!=3
           GROUP BY r.slug, r.category ORDER BY r.category, r.slug"""
    ).fetchall()
    with open(HERE / "repo_counts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["repo", "category", "expected_prs", "github_search_url", "observed_prs", "difference", "reviewer_notes"])
        for c in counts:
            url = (f"https://github.com/{c['slug']}/pulls?q=is%3Apr+created%3A2025-05-01..2026-11-20")
            w.writerow([c["slug"], c["category"], c["n"], url, "", "", ""])

    # ---- revert-link cases
    rev_rows = con.execute(
        """SELECT r.slug, p.number, p.title, p.body, p.merged_at
           FROM prs p JOIN repos r USING(repo_id)
           WHERE p.detail_status!=3 AND p.title LIKE 'Revert%'
           ORDER BY p.created_at DESC LIMIT 15"""
    ).fetchall()
    with open(HERE / "revert_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["repo", "pr_number", "url", "title", "claimed_target", "target_found", "reviewer_verdict", "notes"])
        for r in rev_rows:
            body = r["body"] or ""
            m = re.search(r"This reverts commit ([0-9a-f]{7,40})", body, re.I)
            cite = re.search(r"(?i)reverts?\s+#(\d+)", body + " " + (r["title"] or ""))
            target = m.group(1) if m else (f"#{cite.group(1)}" if cite else "")
            w.writerow([r["slug"], r["number"], f"https://github.com/{r['slug']}/pull/{r['number']}",
                        r["title"], target, "", "", ""])

    # ---- pattern-hit cases
    patterns = {
        "MCP": r"\bMCP\b|model context protocol",
        "Compaction": r"compact(ion)?|compress(ion)?\b.*context|context.*(compact|compress|truncat)",
        "Sub-agent": r"sub-?agents?|parallel (agent|tool)|multi-?agent",
        "Skills": r"\bskills?\b|AGENTS\.md|CLAUDE\.md|custom instructions",
    }
    with open(HERE / "pattern_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pattern", "repo", "pr_number", "url", "title", "is_substantive", "evidence", "notes"])
        for name, pat in patterns.items():
            q = """SELECT r.slug, p.number, p.title FROM prs p JOIN repos r USING(repo_id)
                   WHERE p.detail_status!=3 AND p.merged_at IS NOT NULL
                     AND (LOWER(p.title) LIKE ? OR LOWER(COALESCE(p.body,'')) LIKE ?)
                   ORDER BY RANDOM() LIMIT 4"""
            key = f"%{name.lower()}%" if name not in ("MCP",) else "%mcp%"
            for r in con.execute(q, (key, key)):
                w.writerow([name, r["slug"], r["number"], f"https://github.com/{r['slug']}/pull/{r['number']}",
                            (r["title"] or "").replace("\n", " "), "", "", ""])

    # ---- self-contained HTML app
    payload = json.dumps(sample_rows, ensure_ascii=False).replace("</", "<\\/")
    import html as _html
    codebook = (HERE / "codebook.md").read_text(encoding="utf-8")
    html = (HTML_TEMPLATE.replace("__DATA__", payload)
            .replace("__CODEBOOK__", _html.escape(codebook)))
    (HERE / "review.html").write_text(html, encoding="utf-8")

    files = ["review_sample.csv", "review_form.csv", "repo_counts.csv",
             "revert_sample.csv", "pattern_sample.csv", "review.html"]
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "database": str(DB.relative_to(ROOT)),
        "sample_size": len(sample_rows),
        "tier_counts": {t: sum(1 for r in sample_rows if r["tier_rule"] == t) for t in TIERS},
        "files": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in files},
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"generated {len(sample_rows)} review rows and {len(files)} files")
    print(json.dumps(manifest["tier_counts"]))


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Human Review — Harness Mining Audit</title>
<style>
  :root{--bg:#f6f4ef;--card:#fff;--ink:#20242b;--muted:#6b7280;--line:#d9d4c8;--accent:#1f5f8b;--ok:#2f7d4f;--bad:#a33a2a}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  header{position:sticky;top:0;z-index:5;background:rgba(246,244,239,.96);border-bottom:1px solid var(--line);padding:12px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
  h1{font-size:15px;margin:0;font-weight:650}
  .grow{flex:1}
  .bar{height:7px;background:#e4dfd4;border-radius:99px;overflow:hidden;width:180px}
  .bar>i{display:block;height:100%;width:0;background:var(--accent);transition:width .2s}
  button{font:inherit;border:1px solid var(--line);background:#fff;padding:6px 11px;border-radius:6px;cursor:pointer}
  button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
  button:disabled{opacity:.45;cursor:default}
  main{max-width:900px;margin:22px auto 80px;padding:0 18px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:22px 24px;box-shadow:0 1px 0 rgba(0,0,0,.03)}
  .meta{color:var(--muted);font-size:12px;display:flex;gap:14px;flex-wrap:wrap;margin-bottom:8px}
  .title{font-size:20px;line-height:1.3;margin:4px 0 10px;font-weight:650}
  a{color:var(--accent)}
  .rule{background:#f0f4f7;border:1px dashed #b9c7d3;border-radius:7px;padding:9px 12px;margin:12px 0;font-size:12.5px;color:#374151;display:flex;gap:18px;flex-wrap:wrap}
  .rule b{font-weight:650;color:#1f2937}
  .q{border-top:1px solid #eee;padding:14px 0 4px}
  .q h3{font-size:13px;margin:0 0 8px;font-weight:650}
  .opts{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  .opt{border:1px solid var(--line);border-radius:999px;padding:5px 11px;cursor:pointer;background:#fff;font-size:13px}
  .opt input{display:none}
  .opt.sel-yes{background:#e7f3ec;border-color:#8cbfa2;color:#1f5d3c}
  .opt.sel-no{background:#fbeae7;border-color:#d9a79c;color:#8a3222}
  select,textarea{font:inherit;border:1px solid var(--line);border-radius:6px;padding:5px 7px;background:#fff}
  textarea{width:100%;min-height:52px;resize:vertical}
  .foot{display:flex;justify-content:space-between;align-items:center;margin-top:18px;gap:10px}
  .counter{color:var(--muted);font-size:12px}
  .hint{color:var(--muted);font-size:12px;margin-top:6px}
  .warn{background:#fff7e6;border:1px solid #f0d49a;color:#7a5313;padding:8px 11px;border-radius:7px;font-size:12.5px;margin-bottom:14px}
  .done{color:var(--ok);font-weight:600}
  details{margin-top:10px}
  summary{cursor:pointer;color:var(--accent);font-size:12.5px}
  .evidence{margin-top:12px;border-top:1px dashed #ddd;padding-top:10px}
  .evidence table{width:100%;border-collapse:collapse;font-size:11.5px;margin:6px 0}
  .evidence th,.evidence td{border-bottom:1px solid #eee;padding:3px 5px;text-align:left;vertical-align:top}
  .evidence th{color:#6b7280;font-weight:600}
  .path{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;word-break:break-all}
  .bodytext{white-space:pre-wrap;background:#faf9f6;border:1px solid #eee;border-radius:6px;padding:8px;font-size:12px;max-height:150px;overflow:auto}
  .commits{margin:4px 0 0 18px;padding:0;font-size:12px;color:#374151}
  .agreebox{margin-top:16px}
  .agreebox table{width:100%;border-collapse:collapse;font-size:13px}
  .agreebox th,.agreebox td{border-bottom:1px solid #eee;padding:6px 8px;text-align:left}
  .codebook{white-space:pre-wrap;font:11.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;background:#faf9f6;border:1px solid #eee;border-radius:6px;padding:12px;max-height:420px;overflow:auto}
  .hidden{display:none!important}
</style>
</head>
<body>
<header>
  <h1>Human Review — Harness Mining Audit</h1>
  <div class="bar"><i id="progress"></i></div>
  <span class="counter" id="counter">0 / 0</span>
  <div class="grow"></div>
  <label class="counter"><input type="checkbox" id="blind"> hide rule labels (blind mode)</label>
  <button id="agree">Agreement</button>
  <button id="export" class="primary">Export CSV</button>
</header>
<main>
  <div class="warn">Work through the records in order. Your answers stay in this browser tab only — do not refresh before exporting. Export writes <code>review_form_filled.csv</code>; send it back with your reviewer name.</div>
  <div id="app"></div>
  <div id="agreement" class="card agreebox hidden"></div>
  <div class="card" style="margin-top:16px">
    <details>
      <summary>How to judge each field (short codebook)</summary>
      <p><b>Title / merge status:</b> open the GitHub link and confirm the title matches and whether the PR is merged, closed-unmerged, or open.</p>
      <p><b>Tier:</b> T1 = bot account or explicit end-to-end autonomous declaration; T2 = co-author trailer or tool signature (Claude Code, Copilot, Devin, Cursor, Aider, Codex, Gemini); T3 = no explicit marker. A human using an unmarked assistant is still T3.</p>
      <p><b>Layer:</b> L1 core loop/state machine/scheduling/retry; L2 prompts/context/memory/config/skills; L3 tools/MCP/sandbox/permissions/providers; L4 tests/CI/eval/telemetry; L0 UI/examples/website; LD docs only.</p>
      <p><b>Change type:</b> structural = core refactor, interface/base-class change, concurrency or security boundary, or cross-layer change with deletions/renames; additive = new files/adapters/tests with little deletion; fix = bug fix that is not structural; docs; test_only; ui.</p>
      <p><b>Confidence:</b> 1 = guess, 5 = certain. Use 2–3 freely; do not force certainty.</p>
    </details>
    <details>
      <summary>Full codebook (embedded)</summary>
      <pre class="codebook">__CODEBOOK__</pre>
    </details>
  </div>
</main>
<script>
const DATA = __DATA__;
const FIELDS = ["title_matches","merge_status_matches","tier_correct","tier_corrected",
  "layer_correct","layer_corrected","change_type_correct","change_type_corrected",
  "confidence_1_5","notes"];
const state = {};
let idx = 0;
let reviewer = "";
const $ = (s) => document.querySelector(s);

function get(id){ if(!state[id]) state[id] = {}; return state[id]; }
function filled(id){ const s=get(id); return ["title_matches","merge_status_matches","tier_correct","layer_correct","change_type_correct"].every(k=>s[k]); }

function opt(name, value, label, current){
  const sel = current === value ? (value==="Y"?"sel-yes":"sel-no") : "";
  return `<label class="opt ${sel}" data-name="${name}" data-value="${value}">
    <input type="radio" name="${name}" value="${value}" ${current===value?"checked":""}>${label}</label>`;
}

function render(){
  const r = DATA[idx], s = get(r.id);
  const tierVal = s.tier_corrected || r.tier_rule;
  const layerVal = s.layer_corrected || r.primary_layer_rule;
  const ctVal = s.change_type_corrected || r.change_type_rule;
  const tierFix = ["T1","T2","T3"].map(v=>`<option value="${v}" ${tierVal===v?"selected":""}>${v}</option>`).join("");
  const layerFix = ["L1","L2","L3","L4","L0","LD","UNCLASSIFIED"].map(v=>`<option value="${v}" ${layerVal===v?"selected":""}>${v}</option>`).join("");
  const ctFix = ["structural","additive","fix","docs","test_only","ui"].map(v=>`<option value="${v}" ${ctVal===v?"selected":""}>${v}</option>`).join("");
  $("#app").innerHTML = `
  <div class="card">
    <div class="meta"><span>${r.id}</span><span>${r.repo} #${r.pr_number}</span><span>${r.created_at}</span><span>${r.merge_status}</span></div>
    <div class="title">${escapeHtml(r.title)}</div>
    <div class="meta"><span>author: <b>${escapeHtml(r.author_login)}</b></span><a href="${r.url}" target="_blank" rel="noopener">open on GitHub ↗</a></div>
    <div class="rule" id="rulebox">
      <span>rule tier: <b>${r.tier_rule}</b></span>
      <span>rule layer: <b>${r.primary_layer_rule}</b></span>
      <span>rule change type: <b>${r.change_type_rule}</b></span>
      <span>all layers: ${r.layers_rule}</span>
    </div>
    <details class="evidence">
      <summary>Evidence: files, commits, PR body (embedded; GitHub link optional)</summary>
      ${r.body_excerpt ? `<div class="bodytext">${escapeHtml(r.body_excerpt)}</div>` : ""}
      <table><thead><tr><th>file</th><th>layer</th><th>+</th><th>−</th></tr></thead><tbody>
      ${(r.files||[]).map(f=>`<tr><td class="path">${escapeHtml(f.path)}</td><td>${escapeHtml(f.layer||"")}</td><td>${f.a??""}</td><td>${f.d??""}</td></tr>`).join("")}
      </tbody></table>
      ${(r.commits||[]).length ? `<ul class="commits">${r.commits.map(c=>`<li>${escapeHtml(c)}</li>`).join("")}</ul>` : ""}
    </details>
    <div class="q"><h3>1. Identity check</h3>
      <div class="opts">Title matches ${opt("title_matches","Y","yes",s.title_matches)}${opt("title_matches","N","no",s.title_matches)}</div>
      <div class="opts" style="margin-top:8px">Merge status matches ${opt("merge_status_matches","Y","yes",s.merge_status_matches)}${opt("merge_status_matches","N","no",s.merge_status_matches)}</div>
    </div>
    <div class="q"><h3>2. Tier attribution</h3>
      <div class="opts">${opt("tier_correct","Y","agree (T1/T2/T3)",s.tier_correct)}${opt("tier_correct","N","disagree → correct label",s.tier_correct)}</div>
      <div class="opts" style="margin-top:8px"><select id="tier_fix">${tierFix}</select></div>
    </div>
    <div class="q"><h3>3. Primary architecture layer</h3>
      <div class="opts">${opt("layer_correct","Y","agree",s.layer_correct)}${opt("layer_correct","N","disagree → correct layer",s.layer_correct)}</div>
      <div class="opts" style="margin-top:8px"><select id="layer_fix">${layerFix}</select></div>
    </div>
    <div class="q"><h3>4. Change type</h3>
      <div class="opts">${opt("change_type_correct","Y","agree",s.change_type_correct)}${opt("change_type_correct","N","disagree → correct type",s.change_type_correct)}</div>
      <div class="opts" style="margin-top:8px"><select id="ct_fix">${ctFix}</select></div>
    </div>
    <div class="q"><h3>5. Confidence and notes</h3>
      <div class="opts">confidence
        <select id="conf">${[1,2,3,4,5].map(v=>`<option value="${v}" ${String(s.confidence_1_5)===String(v)?"selected":""}>${v}</option>`).join("")}</select>
      </div>
      <div style="margin-top:8px"><textarea id="notes" placeholder="optional: why the rule is wrong, or what is ambiguous">${escapeHtml(s.notes||"")}</textarea></div>
    </div>
    <div class="foot">
      <button id="prev" ${idx===0?"disabled":""}>← Previous</button>
      <span class="counter">${filled(r.id)?"<span class='done'>record complete</span>":"five judgements required"}</span>
      <button id="next" class="primary">${idx===DATA.length-1?"Finish":"Next →"}</button>
    </div>
  </div>`;

  document.querySelectorAll(".opt").forEach(el=>{
    el.addEventListener("click", ()=>{
      const name=el.dataset.name, val=el.dataset.value;
      get(r.id)[name]=val;
      document.querySelectorAll(`.opt[data-name="${name}"]`).forEach(x=>x.classList.remove("sel-yes","sel-no"));
      el.classList.add(val==="Y"?"sel-yes":"sel-no");
      updateCounter();
    });
  });
  $("#tier_fix").addEventListener("change", e=>{get(r.id).tier_corrected=e.target.value;});
  $("#layer_fix").addEventListener("change", e=>{get(r.id).layer_corrected=e.target.value;});
  $("#ct_fix").addEventListener("change", e=>{get(r.id).change_type_corrected=e.target.value;});
  $("#conf").addEventListener("change", e=>{get(r.id).confidence_1_5=e.target.value;});
  $("#notes").addEventListener("input", e=>{get(r.id).notes=e.target.value;});
  $("#prev").addEventListener("click", ()=>{ if(idx>0){idx--; render();} });
  $("#next").addEventListener("click", ()=>{ if(idx<DATA.length-1){idx++; render();} else { updateCounter(); alert("All records visited. Export the CSV now."); } });
  updateCounter();
}

function updateCounter(){
  const done = DATA.filter(r=>filled(r.id)).length;
  $("#counter").textContent = `${done} / ${DATA.length} complete`;
  $("#progress").style.width = `${(done/DATA.length)*100}%`;
}

function escapeHtml(s){ return String(s??"").replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }

$("#blind").addEventListener("change", e=>{
  const box=document.getElementById("rulebox");
  if(box) box.classList.toggle("hidden", e.target.checked);
});

function kappa(a,b){
  const n=a.length; if(!n) return NaN;
  let po=0; for(let i=0;i<n;i++) if(a[i]===b[i]) po++;
  po/=n;
  const ca={}, cb={};
  a.forEach(x=>ca[x]=(ca[x]||0)+1); b.forEach(x=>cb[x]=(cb[x]||0)+1);
  let pe=0; new Set([...a,...b]).forEach(c=>{ pe += ((ca[c]||0)/n)*((cb[c]||0)/n); });
  return pe<1 ? (po-pe)/(1-pe) : 1;
}

function finalLabel(r, dim){
  const s = state[r.id] || {};
  const ok = (s[dim+"_correct"]||"").toUpperCase();
  const ruleVal = dim==="layer" ? r.primary_layer_rule : r[dim+"_rule"];
  if(ok==="Y") return ruleVal;
  if(ok==="N") return s[dim+"_corrected"] || "";
  return "";
}

$("#agree").addEventListener("click", ()=>{
  const rows=[["Tier","tier"],["Primary layer","layer"],["Change type","change_type"]];
  let html = `<h3 style="margin-top:0">Agreement with rule engine</h3>
    <p class="counter">Computed in this browser from completed records. For the formal report, use <code>compute_agreement.py</code>.</p>
    <table><thead><tr><th>Dimension</th><th>n</th><th>Accuracy</th><th>Cohen's κ</th></tr></thead><tbody>`;
  for(const [label, dim] of rows){
    const rule=[], human=[];
    for(const r of DATA){
      const h=finalLabel(r,dim);
      if(h){ rule.push(dim==="layer" ? r.primary_layer_rule : r[dim+"_rule"]); human.push(h); }
    }
    if(!rule.length){ html += `<tr><td>${label}</td><td>0</td><td>—</td><td>—</td></tr>`; continue; }
    let acc=0; for(let i=0;i<rule.length;i++) if(rule[i]===human[i]) acc++;
    acc=acc/rule.length;
    const k=kappa(rule,human);
    html += `<tr><td>${label}</td><td>${rule.length}</td><td>${(acc*100).toFixed(1)}%</td><td>${k.toFixed(3)}</td></tr>`;
  }
  html += `</tbody></table>`;
  const done = DATA.filter(r=>filled(r.id)).length;
  html += `<p class="counter" style="margin-top:10px">${done} of ${DATA.length} records complete. Thresholds: tier κ ≥ 0.80, layer κ ≥ 0.65, change type κ ≥ 0.60.</p>`;
  const box=$("#agreement"); box.innerHTML=html; box.classList.remove("hidden"); box.scrollIntoView({behavior:"smooth"});
});

$("#export").addEventListener("click", ()=>{
  reviewer = prompt("Reviewer name (for the CSV):", reviewer) || reviewer;
  if(!reviewer){ alert("A reviewer name is required."); return; }
  const header = ["id","reviewer","review_date",...FIELDS];
  const lines = [header.join(",")];
  const today = new Date().toISOString().slice(0,10);
  for(const r of DATA){
    const s = state[r.id] || {};
    const row = [r.id, reviewer, today, ...FIELDS.map(k=>s[k]??"")];
    lines.push(row.map(v=>`"${String(v).replace(/"/g,'""')}"`).join(","));
  }
  const blob = new Blob([lines.join("\n")], {type:"text/csv;charset=utf-8"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "review_form_filled.csv";
  a.click();
  URL.revokeObjectURL(a.href);
});

render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
