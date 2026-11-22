# Reviewer Instructions — Harness Mining Audit

Version 1.1 · 2026-11-22 · companion to `review.html` and `codebook.md`

This document is the operating manual for the 120-record human audit. It tells you exactly what to click, what to compare, how to resolve the hard cases, and how your answers become a Cohen's κ. `EXAMPLES.md` contains ten fully worked records, including five where the rule is wrong on purpose.

---

## 1. What this audit is, and is not

You are auditing **three automated instruments**:

1. the GitHub mining pipeline (did it capture the right PR, title, author, merge status?);
2. the attribution rule (is this PR autonomous-agent, co-authored, or unmarked?);
3. the architecture mapping (which layer is the substantive change, and what kind of change is it?).

You are **not** judging whether the PR is good, whether the agent is competent, whether the design is wise, or whether the authors' thesis is correct. A PR can be low quality and still be correctly labelled T1/L4/fix.

You are also not re-labelling the whole corpus. You see a stratified sample of 120 records; your agreement statistics describe the instruments, not the population prevalence.

---

## 2. Before you start

- Open `review.html` in a browser. It embeds the sample, evidence, codebook, and the κ calculator; no server is needed.
- Use one reviewer identity per form. Reviewer A and Reviewer B fill separate copies independently.
- Budget **2–3 minutes per record**, about **4–6 hours** for 120 records. Split into three sittings; answers autosave in the browser.
- Do not open another reviewer's form before submitting yours.
- Do not ask the rule author what a record "should" be. Ask about the codebook, not the answer.
- If you refresh or close the tab, the app restores your answers from `localStorage`. Use **Export CSV** when finished.

---

## 3. Screen anatomy

Each record has, from top to bottom:

| Block | What it contains | How to use it |
|---|---|---|
| Header line | record id, repo, PR number, created date, merge status | identity check |
| Title | PR title as captured | identity check |
| Metadata | author, association, `+adds/−dels`, files, commits, review comments | scale and contributor type |
| Rule box | rule tier, rule layer, rule change type, all layers | the claim you are auditing |
| Why the rule said this | rule name, matched string, account, layer weights | tells you *why* the instrument fired |
| Evidence | PR body, file table (path, layer, status, +/−), commit subjects | primary evidence for layer and type |
| Diff excerpt | first 7 KB of the GitHub diff | decisive for change type and ambiguous layers |
| Questions 1–5 | identity, tier, layer, change type, confidence/notes | your output |
| Unreviewable | checkbox | only when the record cannot be judged |
| Agreement | browser-side κ over completed records | progress check |

The rule box is deliberately visible. This is an **audit**, not a blind replication: you are asked to agree or disagree with a specific claim, and to record the correct value when you disagree.

---

## 4. The six decisions

For every record you produce six values:

1. `title_matches` — Y/N
2. `merge_status_matches` — Y/N
3. `tier_correct` — Y/N, plus `tier_corrected` if N
4. `layer_correct` — Y/N, plus `layer_corrected` if N
5. `change_type_correct` — Y/N, plus `change_type_corrected` if N
6. `confidence_1_5` and `notes`; optionally `unreviewable`

A record is complete when the five judgements are present, or when `unreviewable` is checked.

---

## 5. Decision rules

### 5.1 Identity

Open the GitHub link. Check three things:

- the PR number in the URL equals the record's `pr_number`;
- the title on GitHub equals the embedded title (minor whitespace/case differences are fine);
- the merge status matches: `merged`, `closed-unmerged`, or `open`.

If the PR is deleted or the repository is gone, mark `unreviewable` and say so. If the title has been edited since capture but the number and merge status are right, mark `title_matches=N` and note "title edited after capture" — do not mark the whole record unreviewable.

### 5.2 Tier

Apply the first matching test.

**Test 1 — bot account.** Login ends in `[bot]`, or the GitHub page identifies the account as a bot/app, or the login is in the known automation list (`copilot-swe-agent`, `devin-ai-integration`, `opencode-agent`, `cline-cloud`, `continue`, `cursor`, `codegen-sh`, `google-labs-jules`, `swe-agent`, `aider`, `gemini-cli`, `cubic-dev-ai`, `hf-security-analysis`, `blacksmith-sh`, `ellipsis-dev`). → **T1**.

**Test 2 — explicit autonomous declaration.** The body says the change was generated end-to-end by an AI, with no human authorship, e.g. "This PR was created entirely by an AI agent", "no human code was written". → **T1**.

**Test 3 — positive co-authorship artifact.** A commit trailer (`Co-Authored-By: Claude`, `Co-authored-by: Cursor`, `Made-with: Cursor`), a tool signature (`Generated with [Claude Code]`, `aider wrote 62% of the code`), or a structured `AI-assisted: yes` field. → **T2**.

**Test 4 — none of the above.** → **T3**, the unmarked baseline.

Critical distinctions:

- **GitHub App token used by a human is not T1 by itself.** If the page shows a person and no `[bot]` suffix, the account is a person even if the API reports `type=Bot`. Check the profile: a human profile with a normal avatar and activity is T3 unless a trailer exists.
- **A bot that only mirrors code is not an agent.** Copybara/Copyberry and dependency/release bots were excluded before sampling. If one appears, mark `tier_correct=N` and note "excluded bot leaked into sample".
- **"I used Copilot" in prose is not T2.** Only a trailer, a tool signature, or a structured field counts.
- **A human who rewrote most of an agent's PR is still T1.** Attribution follows initiation and control, not line count.
- **A docs-only PR from a bot is still T1.** Tier is about authorship, not layer. Do not "correct" T1 to T3 because the change is trivial.

### 5.3 Layer

First decide whether the PR is **test-only** or **docs-only**:

- If every changed file is a test/fixture/benchmark → layer **L4**, change type `test_only`.
- If every changed file is documentation (`.md`, docs site, README, changelog) → layer **LD**, change type `docs`. Exception: `.claude/`, `.clinerules/`, `.agents/`, `.gemini/`, `.roo/`, `queries/`, `prompts/` are runtime rules/prompts → **L2**.

If the PR mixes implementation with tests or docs, **ignore tests, docs, and generated files when choosing the primary layer.** A 1-line UI change with a 300-line test is **L0**, not L4. This is the single most common rule error in the sample.

Then choose the **primary layer** by substantive line weight among implementation files:

| Layer | What belongs | Typical paths |
|---|---|---|
| **L1** core loop | turn loop, state machine, task/sub-agent scheduling, planning/reflection, retry/fallback, termination, concurrency model | `core/controller`, `core/task`, `core/loop`, `session`, `machine`, `agent` (when it is the runner) |
| **L2** context & memory | system prompts, tool *descriptions*, compaction/truncation, RAG/indexing, session persistence, rules/skills, configuration loading | `core/prompts`, `context`, `memory`, `skills`, `config`, `*.md` under prompt dirs |
| **L3** tools & sandbox | tool implementations, MCP, shell/browser/file executors, patch application, permissions, sandbox, provider adapters, external protocols | `tools`, `mcp`, `sandbox`, `providers`, `llm`, `api`, `runtime` |
| **L4** eval & infra | tests, benchmarks, CI, telemetry, tracing, build scripts, lint/type config | `test`, `__tests__`, `.github/`, `Dockerfile`, `pyproject.toml` |
| **L0** product surface | webview/UI, TUI rendering, desktop shell, website, examples, i18n | `webview-ui`, `gui`, `packages/ui`, `components`, `*.tsx`, `*.css` |
| **LD** docs | README, docs site, changelog, comment-only markdown | `docs/`, `README`, `CHANGELOG` |

Tie-breaks:

1. Test/doc/generated files never decide the primary layer in a mixed PR.
2. If two implementation layers tie on line weight, prefer the **lower-numbered** layer (L1 > L2 > L3 > L4 > L0 > LD).
3. A change to a shared type used by the loop is **L1** if it changes the loop's contract; a model-catalog or provider-type entry is **L3**, even if it sits under a `types/` package.
4. A prompt/tool description file is **L2** (context), not L3 (tool implementation). The implementation that executes the tool is L3.
5. A skills refresh controller (`refreshSkills.ts`) is **L2**, not L1, even if it lives under `src/core/controller/`. It manages skills, not the agent loop.
6. A security fix in a UI component is **L0**; a security fix in the exec/tool layer is **L3**; a security fix that changes the loop's authorization contract is **L1**.

### 5.4 Change type

Apply in order:

1. **test_only** — only tests/fixtures/benchmarks changed.
2. **docs** — only documentation changed.
3. **ui** — only product-surface files changed (plus optional tests).
4. **structural** — the change refactors the core loop, changes an interface/base class/contract, changes concurrency or the security model, or is a cross-layer change with substantial deletions/renames. Require at least one of: core layer + deletion ratio > 0.3; a renamed/deleted interface file; ≥2 harness layers with ≥10 files; or a refactor/migrate/rewrite title **and** a real structural diff.
5. **additive** — new files/adapters/tools/tests/prompt text with little deletion and no core rewrite.
6. **fix** — a bug, crash, regression, or compatibility repair that is not structural.

`structural` is not a synonym for "large". A 500-line new model catalog is **additive**; a 30-line deletion of an unused loader used by the task controller can be **structural**. A compatibility bump that only edits a version constant is a **fix**.

### 5.5 Confidence

| Score | Anchor |
|---|---|
| 5 | The diff and the GitHub page are unambiguous; a second reviewer would reach the same label. |
| 4 | Clear, with one minor ambiguity (e.g., a test file accompanies a UI fix). |
| 3 | The primary layer depends on a judgment call (shared type, prompt vs tool, controller vs loop). |
| 2 | The diff is truncated, the PR mixes several concerns, or files are renamed beyond recognition. |
| 1 | You are guessing; say why in notes. |

Do not inflate confidence to improve agreement. A confident 5 on a wrong label is worse than an honest 2.

### 5.6 Unreviewable

Check this only when:

- the repository or PR is deleted and there is no usable file list;
- the patch is empty **and** the file list is missing or unreadable;
- the record is a duplicate of another record (note the duplicate id).

An empty patch alone is **not** enough: if the file list and commit subjects are present, judge from them and note "no diff; judged from file list". Four records in this sample have empty diffs and are still judgeable.

---

## 6. Hard-case matrix

| Case | Decision | Why |
|---|---|---|
| Bot opens a docs-only PR | T1, LD, docs | Tier is authorship; layer is docs. |
| Human uses Cursor but no trailer | T3 | No positive artifact. |
| Human + `Co-Authored-By: Claude` | T2 | Trailer is the artifact. |
| `cline-cloud[bot]` deletes a core loader | T1, L1, structural | Bot account; 355-line deletion in `core/task`; shared tools contract changes. |
| `roo-code-cte[bot]` adds a provider model | T1, **L3**, additive | Provider catalog, not the loop; `types/providers` is L3. |
| `copilot-swe-agent` edits one test file | T1, L4, **test_only** | Test-only change; "fix" in the title does not make it a code fix. |
| `opencode-agent` fixes a TUI dialog (1 product line + 34 test lines) | T1, **L0**, ui (or fix) | Tests do not decide the primary layer; the product change is UI. |
| `Co-Authored-By: Claude` refactors `refreshSkills.ts` | T2, **L2**, structural | Skills are context/memory; the controller path alone does not make it L1. |
| PR contains only `.cursor/plans/*.md` | T2, LD, **docs** | Planning markdown is documentation, not structural code. |
| PR mixes 3 docs + 2 CI workflows | L4, additive/fix | CI is infrastructure; docs do not decide the layer. |
| PR changes only `package-lock.json` | GEN; exclude | Generated/lock files are outside the taxonomy. |
| PR title says "refactor" but diff is a 3-line rename | fix or additive | Structural requires a real structural diff, not a keyword. |

---

## 7. Worked examples

`EXAMPLES.md` contains ten records from this exact sample, with the embedded files, diff excerpt, the correct answers, and the reasoning. Read at least the first five before starting. Five of the ten are deliberate rule errors; they teach you what "disagree" looks like.

Quick index:

| Example | Record | Rule says | Correct answer | Lesson |
|---|---|---|---|---|
| E1 | S012 | T1/LD/docs | agree | bot + docs is still T1 |
| E2 | S001 | T3/L2/fix | agree | prompts beat tool implementations for layer |
| E3 | S003 | T2/L3/additive | agree | co-author trailer + new tool |
| E4 | S016 | T1/L1/structural | agree | deletion in `core/task` is core |
| E5 | S015 | T1/L0/ui | agree | CSS/TSX only |
| E6 | S026 | T1/L4/fix | **test_only** | title "fix" ≠ code fix |
| E7 | S002 | T1/L1/additive | **L3** | provider catalog is not the loop |
| E8 | S014 | T1/L4/fix | **L0** | tests do not set the primary layer |
| E9 | S022 | T2/L1/structural | **L2** | skills controller is context, not loop |
| E10 | S046 | T2/LD/structural | **docs** | planning markdown is not structural code |

---

## 8. Two-reviewer protocol

1. **Reviewer A** and **Reviewer B** audit the same 120 records independently. Neither sees the other's form.
2. Export `review_form_filled_A.csv` and `review_form_filled_B.csv`.
3. Compute per-reviewer agreement with the rule:

```bash
python3 compute_agreement.py --form review_form_filled_A.csv --out agreement_A.md
python3 compute_agreement.py --form review_form_filled_B.csv --out agreement_B.md
```

4. **Adjudicator** opens the rows where A and B disagree, reads the same embedded evidence, and writes `review_form_adjudicated.csv` with the final labels. The adjudicator may consult the codebook but not the rule author's intent.
5. Report both reviewer-level κ and adjudicated κ. Do not report only the better one.

If a dimension fails the threshold, revise the codebook or the rule, draw a **fresh** sample with a new seed, and audit again. Do not tune on the same 120 records and report the tuned κ as independent.

---

## 9. Export and agreement report

The HTML app exports `review_form_filled.csv` with these columns:

```
id, reviewer, review_date, title_matches, merge_status_matches,
tier_correct, tier_corrected, layer_correct, layer_corrected,
change_type_correct, change_type_corrected, confidence_1_5,
unreviewable, notes
```

Run:

```bash
python3 compute_agreement.py \
  --form review_form_filled.csv \
  --sample review_sample.csv \
  --counts repo_counts.csv
```

Outputs `agreement_report.md` and `agreement_summary.json`. The report includes accuracy, κ, the most common rule→human corrections, mean confidence, and repository count deviations.

Thresholds: tier κ ≥ 0.80, layer κ ≥ 0.65, change type κ ≥ 0.60, identity 100%, repo count deviation ≤ 1%.

---

## 10. Common mistakes

1. **Letting tests decide the layer.** A test-heavy PR is L4 only if it is test-only. Otherwise the implementation decides.
2. **Treating "fix" in the title as the change type.** A test-only fix is `test_only`; a compatibility bump is `fix`; a contract rewrite is `structural`.
3. **Calling every `types/` change L1.** Provider catalogs and model IDs are L3.
4. **Calling every `core/` path L1.** `core/prompts` is L2, `core/util` is usually L4, `core/controller/file/refreshSkills` is L2.
5. **Calling a bot docs PR T3.** Tier is authorship.
6. **Marking a missing diff as unreviewable.** If files and commits are present, judge and note the limitation.
7. **Using confidence 5 for a judgment call.** Use 3 when the boundary is genuinely contested.
8. **Skipping notes on disagreements.** Every `N` needs a one-line reason with a file or hunk.
9. **Changing an earlier answer to match the rule.** Record your first judgment; disagreement is the data.
10. **Reporting only one reviewer.** The protocol needs A, B, and an adjudicated file.

---

## 11. Time plan

| Session | Records | Focus |
|---|---|---|
| 1 (90 min) | S001–S040 | read the codebook; do 5 examples first; expect to be slow |
| 2 (90 min) | S041–S080 | steady state; watch for test-heavy and provider PRs |
| 3 (90 min) | S081–S120 | finish; export; run agreement |
| Adjudication (60 min) | disagreements | A + B + adjudicator |

If you fall behind, do not skip the notes. A smaller complete batch with reasons is more useful than 120 rushed rows.

---

## Appendix: field reference

| Field | Allowed values | Meaning |
|---|---|---|
| `title_matches` | Y / N | GitHub title equals embedded title |
| `merge_status_matches` | Y / N | merged / closed-unmerged / open matches |
| `tier_correct` | Y / N | rule tier is right |
| `tier_corrected` | T1 / T2 / T3 | required when `tier_correct=N` |
| `layer_correct` | Y / N | rule primary layer is right |
| `layer_corrected` | L1 / L2 / L3 / L4 / L0 / LD | required when `layer_correct=N` |
| `change_type_correct` | Y / N | rule change type is right |
| `change_type_corrected` | structural / additive / fix / docs / test_only / ui | required when `change_type_correct=N` |
| `confidence_1_5` | 1–5 | see §5.5 |
| `unreviewable` | Y / blank | only under §5.6 |
| `notes` | free text | mandatory for every N and every unreviewable |
