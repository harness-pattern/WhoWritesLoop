#!/usr/bin/env python3
"""Rule engine: Tier attribution, architecture layer mapping, change type.

Usage: python3 pipeline/rules.py [--recompute]
Reads/writes data/evolution2watch.sqlite.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "pipeline" / "config" / "repos.yaml"

# ------------------------------------------------------------------ path layer rules
TEST_RE = re.compile(
    r"(^|/)(__tests__|tests?|e2e|evals?|benchmarks?|test_data|fixtures|test-fixtures|integration_tests)(/|$)"
    r"|(\.|_)(test|spec|vitest|e2e|cy)\.[a-z]+$|(^|/)test_[^/]+\.py$|_test\.py$|(^|/)__snapshots__(/|$)",
    re.I,
)
DOC_RE = re.compile(r"\.(md|mdx|rst|txt)$|(^|/)(docs?|website|site/docs|contributing)/|^README|^CHANGELOG|^LICENSE", re.I)
CI_RE = re.compile(
    r"^\.github/|^\.gitlab-ci|^\.circleci|^Dockerfile|(^|/)docker/|^Makefile$|^pyproject\.toml$"
    r"|^package\.json$|^tsconfig[^/]*\.json$|\.lock$|^\.eslintrc|^biome\.json$|^ruff\.toml$"
    r"|^\.prettierrc|^vitest\.|^vite\.config|^jest\.config|^playwright\.config|^stryker\.config"
    r"|^electron-builder|^\.husky/|^helm/|^\.dockerignore|^\.gitignore$"
    ,
    re.I,
)
UI_RE = re.compile(
    r"(^|/)(webview-ui|webview|gui|packages/ui|packages/tui|packages/desktop|packages/session-ui"
    r"|packages/app|apps/cli|apps/cline-hub|apps/examples|apps/docs|services/site|src/components"
    r"|src/hooks|src/i18n|src/icons|src/themes|public|assets|screenshots|test-evidence|\.screenshots)(/|$)"
    r"|^src/.*\.(tsx|css|scss)$",
    re.I,
)

GENERATED_RE = re.compile(
    r"(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lock|Cargo\.lock|poetry\.lock|uv\.lock|go\.sum)$"
    r"|\.(min\.js|min\.css)$|\.generated\.[a-z]+$|\.gen\.[a-z]+$|openapi\.json$|\.patch$|LICENSES[^/]*\.html$",
    re.I,
)

# repo-specific: ordered (regex, layer)
REPO_RULES: dict[str, list[tuple[str, str]]] = {
    "openai/codex": [
        (r"^codex-rs/core/src/(context|context_manager)/", "L2"),
        (r"^codex-rs/core/src/(tools|unified_exec|mcp_tool_call|exec_policy|guardian|plugins)/", "L3"),
        (r"^codex-rs/core/src/(state|config)/", "L2"),
        (r"^codex-rs/core/", "L1"),
        (r"^codex-rs/(state|thread-store|config|skills|hooks)/", "L2"),
        (r"^codex-rs/(exec-server|apply-patch|codex-mcp|rmcp-client|windows-sandbox-rs"
         r"|linux-sandbox|network-proxy|core-plugins|ext)/", "L3"),
        (r"^codex-rs/(app-server|app-server-protocol|protocol|codex-api|login|utils)/", "L3"),
        (r"^codex-rs/tui/", "L0"),
        (r"^codex-rs/(cli|exec|mcp-server)/", "L0"),
        (r"^sdk/", "L0"),
    ],
    "google-gemini/gemini-cli": [
        (r"^packages/core/src/(core|agents|scheduler)/", "L1"),
        (r"^packages/core/src/(context|prompts|config|services)/", "L2"),
        (r"^packages/core/src/(tools|mcp|sandbox|policy|safety|code_assist)/", "L3"),
        (r"^packages/core/src/(telemetry|utils)/", "L4"),
        (r"^packages/(sdk|a2a-server)/", "L3"),
        (r"^packages/vscode-ide-companion/", "L0"),
        (r"^packages/cli/", "L0"),
        (r"^\.gemini/", "L2"),
        (r"^tools/(caretaker-agent|gemini-cli-bot)/", "L4"),
    ],
    "anomalyco/opencode": [
        (r"^packages/(core|opencode)/src/(cli|cmd|tui)/", "L0"),
        (r"^packages/(core|opencode)/src/(session|machine|automation)/", "L1"),
        (r"^packages/(core|opencode)/src/(database|config|project)/", "L2"),
        (r"^packages/(core|opencode)/src/(tool|plugin|plugins|mcp|codemode|shell|pty|persistent-pty|environment|filesystem|worktree)/", "L3"),
        (r"^packages/(ai|server|protocol|schema|client|sdk)/", "L3"),
        (r"^packages/(core|opencode)/src/", "L1"),
        (r"^packages/(util|data)/", "L2"),
    ],
    "Aider-AI/aider": [
        (r"^aider/coders/", "L1"),
        (r"^aider/(main|commands|editor)\.py$", "L1"),
        (r"^aider/(prompts|repomap|history|repo|special)\.py$", "L2"),
        (r"^aider/(query|queries)/", "L2"),
        (r"^aider/(llm|models|openrouter|linter|run_cmd|diffs|sendchat)\.py$", "L3"),
        (r"^aider/(io|gui|args|args_formatter|onboarding|help|help_pats|waiting|voice|watch|format_settings|copypaste|mdstream|analytics|dump|report|urls|versioncheck|deprecated|exceptions|__main__|__init__|utils)\.py$", "L0"),
        (r"^scripts/", "L4"),
    ],
    "cline/cline": [
        (r"^src/core/", "L1"),
        (r"^apps/vscode/src/core/(controller|hooks|context|prompts)/", "L1"),
        (r"^apps/vscode/src/core/(storage|workspace|mentions)/", "L2"),
        (r"^apps/vscode/src/core/", "L1"),
        (r"^sdk/packages/core/src/(session|runtime|tasks|cron)/", "L1"),
        (r"^sdk/packages/core/src/(services|extensions|hub|cline-core|remote|artifacts)/", "L3"),
        (r"^sdk/packages/core/src/(auth|account|cloud|settings|logging|types|hooks)/", "L2"),
        (r"^sdk/packages/llms/", "L3"),
        (r"^sdk/packages/", "L1"),
        (r"^apps/vscode/src/services/", "L3"),
        (r"^apps/vscode/src/(shared|integrations|hosts)/", "L1"),
        (r"^apps/vscode/", "L0"),
        (r"^evals/", "L4"),
        (r"^\.(clinerules|claude|agents)/", "L2"),
    ],
    "continuedev/continue": [
        (r"^core/(edit|diff)/", "L1"),
        (r"^core/nextEdit/", "L0"),
        (r"^core/(context|indexing|promptFiles|config|data)/", "L2"),
        (r"^core/(tools|llm|protocol)/", "L3"),
        (r"^packages/(openai-adapters|config-yaml|continue-sdk)/", "L3"),
        (r"^core/autocomplete/", "L0"),
        (r"^core/util/", "L1"),
        (r"^extensions/", "L0"),
        (r"^gui/", "L0"),
    ],
    "RooCodeInc/Roo-Code": [
        (r"^src/core/(prompts|config|condense|context-management|mentions|task-persistence)/", "L2"),
        (r"^src/core/(tools|auto-approval|protect|diff|ignore|environment)/", "L3"),
        (r"^src/core/webview/", "L0"),
        (r"^src/core/", "L1"),
        (r"^src/services/", "L3"),
        (r"^src/api/", "L3"),
        (r"^packages/types/", "L1"),
        (r"^packages/", "L1"),
        (r"^webview-ui/", "L0"),
        (r"^apps/cli/", "L0"),
        (r"^apps/docs/", "LD"),
        (r"^\.roo/", "L2"),
    ],
    "OpenHands/OpenHands": [
        (r"^openhands/(controller|agenthub)/", "L1"),
        (r"^openhands/(memory|core/prompts|core/config)/", "L2"),
        (r"^openhands/(runtime|tools|security|server|events)/", "L3"),
        (r"^openhands/", "L1"),
        (r"^(frontend|src|electron)/", "L0"),
        (r"^(docker|helm|config|tools|bin|examples|scripts)/", "L4"),
    ],
    "SWE-agent/SWE-agent": [
        (r"^sweagent/(agent|run)/", "L1"),
        (r"^sweagent/(tools|environment)/", "L3"),
        (r"^tools/", "L3"),
        (r"^config/", "L2"),
        (r"^sweagent/api/", "L3"),
        (r"^sweagent/(inspector|utils)/", "L4"),
        (r"^trajectories/", "L4"),
    ],
    "SWE-agent/mini-swe-agent": [
        (r"^src/minisweagent/(agents|run)/", "L1"),
        (r"^src/minisweagent/(environments|tools|models)/", "L3"),
        (r"^src/minisweagent/config/", "L2"),
        (r"^src/minisweagent/utils", "L4"),
    ],
    "QwenLM/qwen-code": [
        (r"^packages/core/src/(core|agents|scheduler)/", "L1"),
        (r"^packages/core/src/(context|prompts|config|services)/", "L2"),
        (r"^packages/core/src/(tools|mcp|sandbox|policy|safety)/", "L3"),
        (r"^packages/core/src/telemetry/", "L4"),
        (r"^packages/(cli|web-shell|vscode-ide-companion|qwen-live|live-host)/", "L0"),
        (r"^packages/(sdk-[^/]+|acp-bridge|managed-agent-server|cua-driver|channels)", "L3"),
        (r"^docs/", "LD"),
    ],
    "aaif-goose/goose": [
        (r"^crates/goose/src/agents/", "L1"),
        (r"^crates/goose/src/(session|config|prompts|recipe|skills)/", "L2"),
        (r"^crates/goose/src/(providers|mcp|security|plugins|slash_commands|acp)/", "L3"),
        (r"^crates/goose-mcp/", "L3"),
        (r"^crates/goose-cli/", "L0"),
        (r"^ui/", "L0"),
        (r"^documentation/", "LD"),
    ],
    "OpenHands/software-agent-sdk": [
        (r"^openhands-sdk/openhands/sdk/(agent|conversation|automation|subagent|launch)/", "L1"),
        (r"^openhands-sdk/openhands/sdk/(context|condenser|workspace|settings|skills|prompts)/", "L2"),
        (r"^openhands-sdk/openhands/sdk/(tool|llm|mcp|security|secret|git|hooks|io|event|extensions)/", "L3"),
        (r"^openhands-sdk/openhands/sdk/(observability|testing|logger|utils)/", "L4"),
        (r"^openhands-(tools|agent-server)/", "L3"),
        (r"^clients/", "L3"),
        (r"^examples/", "LD"),
    ],
    "browser-use/browser-use": [
        (r"^browser_use/(cli|skill_cli)/", "L0"),
        (r"^browser_use/dom/", "L3"),
        (r"^apps/", "L0"),
        (r"^browser_use/agent/", "L1"),
        (r"^browser_use/(browser|tools|mcp|repl)/", "L3"),
        (r"^browser_use/skills/", "L2"),
        (r"^browser_use/telemetry/", "L4"),
        (r"^skills/", "L4"),
    ],
    "openai/openai-agents-python": [
        (r"^src/agents/(run_internal|realtime|voice|handoffs)/", "L1"),
        (r"^src/agents/(agent|run|result|stream_events)\.py$", "L1"),
        (r"^src/agents/memory/", "L2"),
        (r"^src/agents/(sandbox|models|mcp|extensions)/", "L3"),
        (r"^src/agents/(tool_guardrails|tool_context)\.py$", "L3"),
        (r"^src/agents/(tracing|util|testing)/", "L4"),
        (r"^packages/", "L4"),
        (r"^(examples|docs)/", "LD"),
    ],
    "mastra-ai/mastra": [
        (r"^packages/core/src/(agent|agent-controller|loop|workflows)/", "L1"),
        (r"^packages/core/src/(storage|workspace|processors|knowledge|stream)/", "L2"),
        (r"^packages/memory/", "L2"),
        (r"^packages/rag/", "L2"),
        (r"^packages/core/src/(tools|llm)/", "L3"),
        (r"^packages/(server|mcp|client-sdks|deployers|auth)/", "L3"),
        (r"^stores/", "L2"),
        (r"^mastracode/factory/src/(routes|integrations)/", "L0"),
        (r"^packages/(evals|datasets)/", "L4"),
        (r"^packages/core/src/(evals|datasets)/", "L4"),
        (r"^packages/(playground|playground-ui|cli)/", "L0"),
        (r"^mastracode/(tui|factory-ui)/", "L0"),
        (r"^(docs|templates)/", "LD"),
    ],
    "crewAIInc/crewAI": [
        (r"^lib/crewai/src/crewai/(agents|flow|crew|task|process)/", "L1"),
        (r"^lib/crewai/src/crewai/(memory|knowledge|rag)/", "L2"),
        (r"^lib/crewai/src/crewai/(tools|llms|mcp|a2a)/", "L3"),
        (r"^lib/crewai/src/crewai/llm\.py$", "L3"),
        (r"^lib/crewai-tools/", "L3"),
        (r"^lib/crewai-files/", "L3"),
        (r"^lib/crewai/src/crewai/experimental/", "L1"),
        (r"^lib/crewai/src/crewai/(telemetry|utilities)/", "L4"),
        (r"^lib/crewai/src/crewai/cli/", "L0"),
        (r"^docs/", "LD"),
    ],
    "langchain-ai/langgraph": [
        (r"^libs/langgraph/langgraph/(pregel|graph|channels|func)/", "L1"),
        (r"^libs/langgraph/langgraph/runtime\.py$", "L1"),
        (r"^libs/(checkpoint|checkpoint-|langgraph/langgraph/store)/", "L2"),
        (r"^libs/prebuilt/", "L1"),
        (r"^libs/cli/", "L0"),
        (r"^libs/sdk-py/", "L3"),
        (r"^examples/", "LD"),
    ],
    "google/adk-python": [
        (r"^src/google/adk/(flows|agents|workflow|runners)/", "L1"),
        (r"^src/google/adk/(sessions|memory|artifacts)/", "L2"),
        (r"^src/google/adk/(tools|models|mcp|auth|plugins|integrations|a2a)/", "L3"),
        (r"^src/google/adk/(evaluation|telemetry)/", "L4"),
        (r"^src/google/adk/(cli|web)/", "L0"),
    ],
    "huggingface/smolagents": [
        (r"^src/smolagents/agents\.py$", "L1"),
        (r"^src/smolagents/(memory|serialization)\.py$", "L2"),
        (r"^src/smolagents/(models|tools|default_tools|local_python_executor|remote_executors|mcp_client|tool_validation)\.py$", "L3"),
        (r"^src/smolagents/(monitoring|utils)\.py$", "L4"),
        (r"^src/smolagents/(gradio_ui|cli|vision_web_browser)\.py$", "L0"),
    ],
}

# ------------------------------------------------------------------ tier rules
TIER1_TEXT = [
    re.compile(r"(?i)(fully|entirely|end-to-end)\s+(autonomous(ly)?|automated|generated)\s+by\s+(an?\s+)?(ai|agent|bot)"),
    re.compile(r"(?i)this\s+pr\s+was\s+(created|generated|authored)\s+(entirely\s+)?by\s+(an?\s+)?(ai|agent|bot)"),
    re.compile(r"(?i)no\s+human\s+(code\s+)?(was\s+)?(written|authored)"),
]

TIER2_PATTERNS = [
    re.compile(r"(?i)^co-authored-by:\s*.*(claude|anthropic|copilot|devin|cursor|aider|codex|openai|gemini|windsurf)"),
    re.compile(r"(?i)^made-with:\s*(cursor|claude|codex|aider)"),
    re.compile(r"(?i)^generated-by:\s*(claude|codex|aider|cursor)"),
    re.compile(r"(?i)generated\s+with\s+\[?claude\s+code"),
    re.compile(r"(?i)🤖\s*generated\s+with"),
    re.compile(r"(?i)co-authored-by:\s*(claude|devin|copilot|cursor|aider|codex)"),
    re.compile(r"(?i)aider\s+wrote\s+\d+%?\s*of\s+the\s+code"),
    re.compile(r"(?i)this\s+(pr|change|commit)\s+was\s+(written|implemented|assisted)\s+(with|by)\s+(claude|codex|copilot|cursor|aider|devin|gemini)"),
    re.compile(r"(?i)ai[- ]?(assisted|generated)\s*[:：]\s*(yes|true|✅)"),
]

AGENT_KEYWORDS = [
    ("claude_code", r"claude|anthropic"),
    ("github_copilot", r"copilot"),
    ("devin", r"devin"),
    ("cursor", r"cursor"),
    ("aider", r"aider"),
    ("codex", r"codex|openai"),
    ("gemini_cli", r"gemini"),
    ("openhands", r"openhands"),
    ("swe_agent", r"swe[- ]?agent"),
    ("jules", r"jules"),
    ("codegen", r"codegen"),
    ("opencode", r"opencode"),
    ("continue_agent", r"continue"),
]

STRUCT_KW = re.compile(r"(?i)\b(refactor|restructure|rewrite|migrate|redesign|decouple|extract|overhaul|rearchitect)\b")
FIX_KW = re.compile(r"(?i)\b(fix|bug|crash|regression|hotfix|broken|error)\b")


def classify_path(slug: str, path: str) -> str:
    if TEST_RE.search(path):
        return "L4"
    prompt_asset = re.match(r"^\.(claude|clinerules|agents|gemini|roo)/", path) or re.search(
        r"(^|/)(queries|prompts)/", path
    )
    if DOC_RE.search(path) and not prompt_asset:
        return "LD"
    if GENERATED_RE.search(path):
        return "GEN"
    if CI_RE.search(path):
        return "L4"
    if re.match(r"^(scripts?|\.pr)/", path):
        return "L4"
    if UI_RE.search(path):
        return "L0"
    for pat, layer in REPO_RULES.get(slug, []):
        if re.match(pat, path):
            return layer
    return "UNCLASSIFIED"


def agent_family_from_text(text: str) -> str | None:
    low = text.lower()
    for fam, pat in AGENT_KEYWORDS:
        if re.search(pat, low):
            return fam
    return None


def attribute_tier(slug, row, commits, agent_bots) -> tuple[str, str | None, dict]:
    login = (row["author_login"] or "").lower()
    atype = row["author_type"] or "User"
    text = (row["title_body"] or "")
    commit_text = "\n".join(c["message"] or "" for c in commits)

    bare = login.replace("[bot]", "")
    if login in agent_bots or bare in agent_bots:
        return "T1", agent_bots.get(login) or agent_bots.get(bare), {
            "rule": "agent_bot_account", "login": login}
    if atype == "Bot" or login.endswith("[bot]"):
        fam = agent_family_from_text(login) or "other_bot"
        return "T1", fam, {"rule": "bot_account", "login": login}

    for rx in TIER1_TEXT:
        m = rx.search(text)
        if m:
            return "T1", agent_family_from_text(m.group(0)) or "other_bot", {
                "rule": "explicit_autonomous", "match": m.group(0)[:120]}

    hay = text + "\n" + commit_text
    for rx in TIER2_PATTERNS:
        m = rx.search(hay)
        if m:
            return "T2", agent_family_from_text(m.group(0)), {"rule": "coauthor_trailer", "match": m.group(0)[:120]}

    return "T3", None, {"rule": "no_marker"}


def change_type(row, file_rows) -> str:
    layers = {f["layer"] for f in file_rows if f["layer"] not in ("L0", "LD")}
    n_files = len(file_rows)
    add = row["additions"] or 0
    dele = row["deletions"] or 0
    total = max(1, add + dele)
    title = (row["title"] or "")
    body = (row["body"] or "")[:3000]
    if not layers:
        if all(f["layer"] == "LD" for f in file_rows):
            return "docs"
        if all(f["layer"] == "L0" for f in file_rows):
            return "ui"
        return "test_only" if all(f["layer"] == "L4" for f in file_rows) else "docs"
    touches_core = "L1" in layers
    structural = (
        (touches_core and dele / total > 0.3)
        or n_files >= 10 and len(layers) >= 2
        or (STRUCT_KW.search(title + "\n" + body) and n_files >= 5)
    )
    if structural:
        return "structural"
    if FIX_KW.search(title):
        return "fix"
    if add and dele / max(1, dele + add) < 0.15 and touches_core is False:
        return "additive"
    return "additive"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recompute", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(CONFIG))
    agent_bots = {k.lower(): v for k, v in cfg["agent_bots"].items()}
    con = db.connect()

    rows = con.execute(
        """SELECT p.*, COALESCE(p.title,'') || '\n' || COALESCE(p.body,'') AS title_body
           FROM prs p WHERE p.detail_status!=3"""
    ).fetchall()
    n_detail = sum(1 for r in rows if r["detail_status"] == 1)
    print(f"labeling {len(rows)} PRs ({n_detail} with details)")

    for r in rows:
        repo = con.execute("SELECT slug FROM repos WHERE repo_id=?", (r["repo_id"],)).fetchone()
        slug = repo["slug"]
        has_detail = r["detail_status"] == 1
        files = con.execute(
            "SELECT path, additions, deletions FROM pr_files WHERE repo_id=? AND number=?",
            (r["repo_id"], r["number"]),
        ).fetchall()
        commits = con.execute(
            "SELECT message FROM pr_commits WHERE repo_id=? AND number=?",
            (r["repo_id"], r["number"]),
        ).fetchall() if has_detail else []

        # layer mapping
        loc = {}
        by_files = {}
        unclass = 0
        test_loc = 0
        total_loc = 0
        file_rows = []
        for f in files:
            layer = classify_path(slug, f["path"])
            if layer == "GEN":
                continue
            w = (f["additions"] or 0) + (f["deletions"] or 0)
            w_eff = max(w, 1)
            loc[layer] = loc.get(layer, 0) + w_eff
            by_files[layer] = by_files.get(layer, 0) + 1
            total_loc += w_eff
            if layer == "UNCLASSIFIED":
                unclass += w_eff
            if layer == "L4":
                test_loc += w_eff
            file_rows.append({"path": f["path"], "layer": layer,
                              "additions": f["additions"], "deletions": f["deletions"]})

        harness_layers = {k for k in loc if k in ("L1", "L2", "L3", "L4")}
        tiers, fam, ev = attribute_tier(slug, r, commits, agent_bots)
        ct = change_type(r, file_rows)

        if not has_detail:
            con.execute(
                "UPDATE prs SET tier=?, agent_family=?, tier_evidence=? WHERE repo_id=? AND number=?",
                (tiers, fam, json.dumps(ev, ensure_ascii=False), r["repo_id"], r["number"]),
            )
            continue

        con.execute(
            """UPDATE prs SET tier=?, agent_family=?, tier_evidence=?, layers=?,
                 layers_by_files=?, layers_touched=?, touches_core=?,
                 core_share=?, test_share=?, unclassified_loc=?, change_type=?
               WHERE repo_id=? AND number=?""",
            (
                tiers, fam, json.dumps(ev, ensure_ascii=False),
                json.dumps(loc, sort_keys=True), json.dumps(by_files, sort_keys=True),
                len(harness_layers), 1 if "L1" in loc else 0,
                round(loc.get("L1", 0) / total_loc, 4) if total_loc else 0.0,
                round(test_loc / total_loc, 4) if total_loc else 0.0,
                unclass, ct, r["repo_id"], r["number"],
            ),
        )
        con.execute(
            "UPDATE pr_files SET layer=? WHERE repo_id=? AND number=?",
            ("", r["repo_id"], r["number"]),
        )
    con.commit()

    # write file layers (per row, vectorized enough for sample sizes)
    for r in rows:
        repo = con.execute("SELECT slug FROM repos WHERE repo_id=?", (r["repo_id"],)).fetchone()
        for f in con.execute("SELECT path FROM pr_files WHERE repo_id=? AND number=?",
                             (r["repo_id"], r["number"])).fetchall():
            con.execute(
                "UPDATE pr_files SET layer=? WHERE repo_id=? AND number=? AND path=?",
                (classify_path(repo["slug"], f["path"]), r["repo_id"], r["number"], f["path"]),
            )
    con.commit()

    print("\nTier distribution (all):")
    for row in con.execute("SELECT tier, COUNT(*) c FROM prs WHERE detail_status!=3 GROUP BY tier ORDER BY c DESC"):
        print(f"  {row['tier']}: {row['c']}")
    print("\nLayer LOC share (all):")
    tot = con.execute("SELECT SUM(additions+deletions) s FROM pr_files").fetchone()["s"] or 1
    for row in con.execute(
        "SELECT layer, SUM(additions+deletions) s FROM pr_files GROUP BY layer ORDER BY s DESC"
    ):
        print(f"  {row['layer']}: {row['s']} ({row['s']/tot:.1%})")
    un = con.execute("SELECT SUM(unclassified_loc) u, SUM(additions+deletions) s FROM prs WHERE detail_status=1").fetchone()
    print(f"\nUNCLASSIFIED share: {(un['u'] or 0)/max(1, un['s'] or 1):.2%}")


if __name__ == "__main__":
    main()
