# Codebook — human audit of harness mining and attribution

This codebook is for reviewers who did **not** build the rule engine. Read it once, then work record by record in `review.html` or `review_form.csv`. The goal is to catch mining errors, not to reproduce the original labels. `INSTRUCTIONS.md` gives the full protocol; `EXAMPLES.md` gives ten worked records, five of which are deliberate rule errors.

---

## 1. What you are judging

For each sampled pull request:

1. **Identity** — does the GitHub page match the row (title, number, merge status)?
2. **Tier** — is the PR autonomous-agent, co-authored/assisted, or unmarked?
3. **Primary layer** — which part of the harness does the change actually touch?
4. **Change type** — is it structural, additive, a fix, docs, test-only, or UI?

You are not judging whether the PR is good, whether the agent is capable, or whether the design is wise.

---

## 2. Tier

Use the first matching rule.

| Tier | Test | Examples |
|---|---|---|
| **T1 autonomous** | The author is a bot account (login ends in `[bot]`, or GitHub reports `type=Bot`), **or** the PR body says the change was generated end-to-end by an AI with no human authorship. | `copilot-swe-agent`, `devin-ai-integration`, `opencode-agent`, `cubic-dev-ai`, `hf-security-analysis`; a human-authored PR whose body says “This PR was created entirely by an AI agent”. |
| **T2 co-authored / assisted** | The PR body or any commit contains a positive artifact: `Co-authored-by: Claude`, `Made-with: Cursor`, `Generated with Claude Code`, `aider wrote 62% of the code`, or a structured “AI-assisted: yes” field. | Claude Code, Codex, Cursor, Aider, Copilot co-author trailers. |
| **T3 unmarked** | No bot account and no positive artifact. A human who used an unmarked assistant is still T3. | Ordinary human PRs; “I used Copilot” in a comment without a trailer is **not** enough for T2 unless the comment is a formal declaration. |

### Tier edge cases

- **Bot account with a human-looking name.** GitHub GraphQL strips `[bot]` from logins. Judge from the GitHub page: if the account is a GitHub App / bot, it is T1. If a human maintainer used an app token, the page still shows a person and is T3.
- **Agent opens a PR, human rewrites most of it.** Still T1; attribution follows initiation and control, not line count.
- **Human opens a PR and an agent commits into it.** T2 if a trailer/signature exists; otherwise T3.
- **Mirror bots** (`copyberry`, `copybara-service`) and dependency/release bots are **out of scope**; they should not appear in the sample. If one does, mark `tier_correct=N` and note “excluded bot”.
- **`cubic-dev-ai`, `hf-security-analysis`, `blacksmith-sh`** are automation accounts. Treat them as T1 only if the PR is a code/docs change; if the account is a CI service making a workflow change, still T1 by the rule, but note the ambiguity.

Worked examples from the sample:

- `S001` browser-use #3141, author `cubic-dev-ai`, docs wording change → **T1** (bot account).
- `S015` qwen-code #6369, author `copilot-swe-agent`, CI triage change → **T1**.
- `S002` adk-python #2658, human author, dependency fix → **T2 only if** a trailer/signature is visible on GitHub; otherwise **T3**. This is a deliberate hard case.
- `S003` langgraph #4741, human author, typo fix, no marker → **T3**.

---

## 3. Layers

Apply this precedence; the first match wins.

1. **Test / benchmark** — path or filename contains `/test/`, `/tests/`, `__tests__`, `spec`, `_test.py`, `test_*.py`, `/e2e/`, `/evals/`, `/benchmarks/` → **L4**.
2. **Generated / lock / bundle** — `package-lock.json`, `pnpm-lock.yaml`, `*.lock`, `*.min.js`, `*.generated.ts`, `*.gen.ts`, `openapi.json`, `*.patch` → **GEN**. Do not assign a harness layer; note it.
3. **Docs** — `*.md`, `*.mdx`, `docs/`, `website/`, `README`, `CHANGELOG`, `LICENSE` → **LD**. Exception: `.claude/`, `.clinerules/`, `.agents/`, `.gemini/`, `.roo/`, `queries/`, `prompts/` are runtime rules/prompts → **L2**.
4. **Product surface** — webview/UI/TUI/desktop, `src/components`, React hooks, website, i18n, images → **L0**.
5. **CI / build / repo config** — `.github/`, Docker, Makefile, `pyproject.toml`, `package.json`, `tsconfig`, lint config → **L4**.
6. **Functional layer** — use the repository map below.

| Layer | What belongs |
|---|---|
| **L1 core loop** | Turn loop, state machine, task/agent scheduling, planning/reflection, retry/fallback, termination, concurrency model, sub-agent orchestration. |
| **L2 context & memory** | System prompts, compaction/truncation, RAG/code indexing, session persistence, rules/skills definitions, configuration loading. |
| **L3 tools & sandbox** | Tool/MCP interfaces, shell/browser/file executors, patch application, permission checks, sandboxing, provider adapters, external protocols/API. |
| **L4 eval & infra** | Tests, benchmarks, CI, telemetry/tracing, build scripts, type/lint config. |
| **L0 product** | Webview/UI, TUI rendering, desktop shell, website, examples, i18n. |
| **LD docs** | README, docs site, changelog, comment-only markdown. |

**Primary layer** is the layer of the substantive implementation change. First decide whether the PR is *test-only* or *docs-only*; if it is, the layer is L4 or LD. If it is mixed, **ignore test, documentation, and generated files when computing line weight**—a 1-line UI change plus a 300-line test is L0, not L4. Then choose the layer with the largest implementation line weight (`additions + deletions`, excluding GEN, tests, and docs). If two layers tie, prefer L1 > L2 > L3 > L4 > L0 > LD.

### Layer edge cases

- A test file that imports core code is **L4**, not L1.
- A comment-only change in a core file is **LD** if the diff contains no executable change; otherwise it takes the file's layer.
- A PR that renames a shared type used by the loop is **L1** if the type is part of the loop contract, even if the file lives in a `shared/` directory.
- A prompt template in `aider/queries/*.md` is **L2**, not LD.
- A CI workflow that changes how tests run is **L4**; a workflow that changes release automation is **L4** too, but note “release automation” in the notes.

---

## 4. Change type

| Type | Test |
|---|---|
| **structural** | Refactors the core loop, changes an interface/base class/contract, changes the concurrency or security model, or is a cross-layer change with substantial deletions/renames. |
| **additive** | Adds files, adapters, tools, tests, or prompt text, with little deletion and no core rewrite. |
| **fix** | Repairs a bug, crash, regression, or compatibility failure without restructuring. |
| **docs** | Only documentation changes. |
| **test_only** | Only tests/benchmarks. |
| **ui** | Only product surface. |

If a PR is both a fix and structural, choose **structural** only when the fix changes an interface/contract or removes/replaces a design; otherwise **fix**. A compatibility bump that deletes branches and rewrites a provider adapter is structural; a one-line version check is a fix.

Worked example: `S006` openai-agents-python #2039, “fix: openai==2.7.0 compatibility”, rule says **structural**. Read the diff: if it only bumps a version or adjusts a call signature, mark **fix** and note the rule error. This is exactly the kind of case the audit is designed to catch.

---

## 5. Confidence

Use the full 1–5 scale:

- **5** — the diff and the GitHub page are unambiguous.
- **4** — clear, minor ambiguity in layer/type.
- **3** — the primary layer depends on a judgment call (e.g., shared type used by the loop).
- **2** — the patch is truncated or the PR mixes several concerns.
- **1** — you are guessing.

Do not inflate confidence to make the agreement look better. A low-confidence disagreement is more useful than a false certainty.

---

## 6. Reviewer conduct

- Do not consult the rule author while labeling a batch.
- Do not look at another reviewer's form before submitting yours.
- Record the first judgment; do not revisit records to “match” the rule.
- If a record is impossible to judge (deleted repo, missing patch), mark `tier_correct=N` only if you can justify it; otherwise leave blank and note “unreviewable”.
- Write notes for every disagreement, citing the file or hunk that changed your mind.
