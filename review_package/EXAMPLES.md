# Worked Examples — Harness Mining Audit

Ten records from the actual 120-record sample. Each shows the embedded evidence, the decision, and the reasoning. **E6–E10 are deliberate rule errors**: they teach the difference between "the rule fired" and "the rule is right". Read E1–E5 before starting; use E6–E10 as calibration for disagreements.

Open the same record in `review.html` by its id to see the full evidence and diff.

| # | Record | Rule | Correct | Verdict | Lesson |
|---|---|---|---|---|---|
| E1 | S012 | T1 / LD / docs | same | agree | explicit AI declaration makes a human account T1 |
| E2 | S001 | T3 / L2 / fix | same | agree | prompt/tool-description files are L2 |
| E3 | S003 | T2 / L3 / additive | same | agree | co-author trailer + new tool |
| E4 | S016 | T1 / L1 / structural | same | agree | deletion in `core/task` is core |
| E5 | S015 | T1 / L0 / ui | same | agree | CSS/TSX only |
| E6 | S026 | T1 / L4 / fix | T1 / L4 / **test_only** | disagree | a test-only fix is not a code fix |
| E7 | S002 | T1 / L1 / additive | T1 / **L3** / additive | disagree | provider catalogs are L3 |
| E8 | S014 | T1 / L4 / fix | T1 / **L0** / **ui** | disagree | tests do not set the primary layer |
| E9 | S022 | T2 / L1 / structural | T2 / **L2** / structural | disagree | a skills loader is context, not the loop |
| E10 | S046 | T2 / LD / structural | T2 / LD / **docs** | disagree | planning markdown is not structural code |

---

## E1 — S012 · OpenHands/software-agent-sdk #2952

**Rule:** T1 / LD / docs — **agree**.

**What the record shows.** Author `smolpaws` (a human-looking login), association `CONTRIBUTOR`. The PR body contains the explicit sentence "This PR was created by an AI". Files: `README.md` only, 2 additions and 1 deletion. The diff adds one line to the setup section ("For local development from this repository, run `make build`…") and updates one documentation link.

**Decision.**

| Field | Value |
|---|---|
| Title / merge | Y / Y (merged) |
| Tier | T1 |
| Layer | LD |
| Change type | docs |
| Confidence | 5 |

**Why.** Tier is authorship, not layer: the author is a person, but the body is a positive end-to-end autonomous declaration, which is Test 2 for T1. The only file is `README.md`, so the layer is LD and the type is docs. A bot or an AI writing a one-line README is still T1/LD/docs.

**What would change it.** A co-author trailer instead of the explicit sentence would make it T2. A code file in the diff would move the layer; docs do not decide a mixed PR.

---

## E2 — S001 · RooCodeInc/Roo-Code #6877

**Rule:** T3 / L2 / fix — **agree**.

**What the record shows.** Author `Hannes Rudolph`, association `NONE`, no trailer or tool signature in the four commits (`Update codebase-search.ts`, `fix: make search_files path parameter optional…`, etc.). Files:

```
L2  MODIFIED  11/7   src/core/prompts/tools/codebase-search.ts
L2  MODIFIED   1/1   src/core/prompts/tools/index.ts
```

The diff changes the tool-description string: it adds a `ToolArgs` parameter, rewrites the `codebase_search` description, and clarifies the optional `path` parameter. No executor, no loop, no test.

**Decision.** T3 / L2 / fix / confidence 5.

**Why.** No bot account and no positive artifact → T3. The change is in the *description* of a tool, not the tool implementation, so it is context (L2), not L3. It repairs a misleading tool description and a parameter signature, so `fix`; it is not a contract rewrite.

**What would change it.** If the diff also changed `src/core/tools/codebaseSearch.ts` (the executor), L3 would compete and could win on line weight. If the author had a `Co-Authored-By: Claude` trailer, tier would be T2.

---

## E3 — S003 · SWE-agent/mini-swe-agent #770

**Rule:** T2 / L3 / additive — **agree**.

**What the record shows.** Author `DhruvBhatia0`, tier evidence `{"rule":"coauthor_trailer","match":"Co-Authored-By: Claude"}`. New files:

```
L3  ADDED  174  src/minisweagent/models/utils/warpgrep.py
L4  ADDED  144  tests/test_warpgrep.py
L3  ADDED   83  src/minisweagent/models/litellm_warpgrep.py
L2  ADDED   44  src/minisweagent/config/warpgrep.yaml
L3  MODIFIED 1  src/minisweagent/models/__init__.py
```

The diff adds a WarpGrep code-search model adapter and its config; no existing code is deleted.

**Decision.** T2 / L3 / additive / confidence 5.

**Why.** The trailer is a positive co-authorship artifact → T2. The dominant implementation layer is L3 (258 lines across the model adapter and registry), with L2 config and L4 tests as support. The change adds a new adapter rather than rewriting one → additive.

**What would change it.** If the PR had replaced an existing search backend and deleted its interface, `structural` would be plausible. A bare config-only PR would be L2/additive.

---

## E4 — S016 · cline/cline #14881

**Rule:** T1 / L1 / structural — **agree**.

**What the record shows.** Author `cline-cloud` (bot account). The PR removes an unused `AgentConfigLoader` and its companion `SubagentToolName`, and updates the shared tool registry:

```
L1  DELETED  0/355  apps/vscode/src/core/task/tools/subagent/AgentConfigLoader.ts
L4  ADDED   63/0    apps/vscode/src/core/storage/StateManager.test.ts
L1  DELETED  0/41   apps/vscode/src/core/task/tools/subagent/SubagentToolName.ts
L1  MODIFIED 0/6    apps/vscode/src/shared/tools.ts
L2  MODIFIED 0/3    apps/vscode/src/core/storage/StateManager.ts
```

**Decision.** T1 / L1 / structural / confidence 5.

**Why.** Bot account → T1. The implementation is dominated by L1 deletions in `core/task/tools/subagent` and a shared tool contract, so L1. Deleting a loader and its exported type changes the sub-agent tool wiring; that is structural, not additive, even though the PR is "just cleanup". The 63-line test is support and does not change the layer.

**What would change it.** If the loader were still referenced and the PR only removed an unused export, it could be `additive` or `fix`. The deleted 355-line class and the shared `tools.ts` edit are what make it structural.

---

## E5 — S015 · anomalyco/opencode #45486

**Rule:** T1 / L0 / ui — **agree**.

**What the record shows.** Author `opencode-agent` (bot). Three product-surface files:

```
L0  MODIFIED  5/0  packages/session-ui/src/components/message-part.css
L0  MODIFIED  2/1  packages/app/src/session/timeline/virtualizer.tsx
L0  MODIFIED  1/0  packages/app/src/session/timeline/message-timeline.tsx
```

The diff threads `workspaceSession` into `VirtualizedTimeline` and adjusts the message accent CSS.

**Decision.** T1 / L0 / ui / confidence 5.

**Why.** All implementation files are UI/session surface, no harness layer is touched. `ui` is the right type because the change is product presentation, not a harness fix. A bot changing only CSS is still T1.

**What would change it.** If the change altered session state semantics rather than presentation, L2 could compete. If it fixed a crash in the virtualizer, `fix` would be defensible; the embedded diff shows a prop/CSS change, so `ui` is the better label.

---

## E6 — S026 · QwenLM/qwen-code #3784

**Rule:** T1 / L4 / fix — **disagree on change type**.

**What the record shows.** Author `copilot-swe-agent` (bot). The only changed file is a test:

```
L4  MODIFIED  15/18  packages/core/src/tools/monitor.test.ts
```

The diff corrects the expected `taskkill` arguments on Windows by adding the missing `stdio` option to the assertion.

**Decision.** T1 / L4 / **test_only** / confidence 5.

**Why.** Bot account → T1; the only file is a test → L4. But the change repairs a *test assertion*, not production behavior. The title says "fix", which is why the rule chose `fix`; the taxonomy's `test_only` is more specific and takes precedence. This is a clean disagreement: `change_type_correct=N`, corrected `test_only`, note "only `monitor.test.ts` changed".

**What would change it.** A simultaneous production change in `monitor.ts` would make it a `fix` with L4/L3 mixed. A new test file with no behavior change is still `test_only`.

---

## E7 — S002 · RooCodeInc/Roo-Code #8655

**Rule:** T1 / L1 / additive — **disagree on layer**.

**What the record shows.** Author `roo-code-cte` (bot). Files:

```
L1  MODIFIED  20/6  packages/types/src/providers/chutes.ts
L4  MODIFIED  22/0  src/api/providers/__tests__/chutes.spec.ts
```

The diff adds `"inclusionAI/Ring-1T-FP8"` to the `ChutesModelId` union and covers it with a provider test.

**Decision.** T1 / **L3** / additive / confidence 4.

**Why.** The rule maps `packages/types/**` to L1 because shared types can be contracts. But this file is a **provider model catalog**—the list of model IDs a provider adapter exposes. It belongs to the provider layer (L3), not the agent loop. The test is support and does not decide the layer. The change adds a model entry → additive.

**What would change it.** If the PR changed the `AgentConfig` type used by the task controller, L1 would be right. The path alone is not enough; read the type.

---

## E8 — S014 · anomalyco/opencode #37674

**Rule:** T1 / L4 / fix — **disagree on layer and type**.

**What the record shows.** Author `opencode-agent` (bot). Files:

```
L4  MODIFIED  34/2  packages/tui/test/cli/tui/dialog-select.test.tsx
L0  MODIFIED   1/1  packages/tui/src/ui/dialog-select.tsx
```

The product change adds `&& store.input !== "mouse"` to the dialog focus condition; the rest is a regression test for mouse selection.

**Decision.** T1 / **L0** / **ui** / confidence 4.

**Why.** The rule counts the 34-line test as L4 and lets it outweigh the 1-line product change. That is the classic test-heavy error: tests support the change but do not define its layer. The substantive change is a TUI behavior fix, so L0. The type is `ui` because only product-surface implementation changed (plus its test); `fix` is defensible if you read it as a bug fix, but the taxonomy's `ui` is more specific for a presentation-only change.

**What would change it.** If the change altered dialog *state semantics* used by the session layer, L2 could compete. If it fixed a crash in a shared component, `fix` would be the better type.

---

## E9 — S022 · cline/cline #9956

**Rule:** T2 / L1 / structural — **disagree on layer**.

**What the record shows.** Author `johnwschoi`, tier evidence `{"rule":"coauthor_trailer","match":"Co-Authored-By: Claude"}`. One file:

```
L1  MODIFIED  7/30  src/core/controller/file/refreshSkills.ts
```

The diff deletes a hand-rolled YAML frontmatter parser and imports the shared `parseYamlFrontmatter` helper, keeping the same `RefreshedSkills` output.

**Decision.** T2 / **L2** / structural / confidence 4.

**Why.** The rule maps `src/core/**` to L1. But this file refreshes **skills**—context/rules—not the agent loop. The `controller/` directory is an implementation detail; the responsibility is L2. The change replaces one parser with another and deletes 30 lines, so `structural` is defensible at L2 even though it is not core.

**What would change it.** If `refreshSkills` also changed when or whether skills are loaded into the prompt pipeline, L2 is still right; if it changed the loop's tool authorization, L1 would be right. Read the call sites, not the directory.

---

## E10 — S046 · aaif-goose/goose #11514

**Rule:** T2 / LD / structural — **disagree on change type**.

**What the record shows.** Author `genarionogueira`, tier evidence `{"rule":"coauthor_trailer","match":"Co-authored-by: Cursor"}`. No diff was cached (empty API response), but the file list is complete: five `.cursor/plans/*.md` files, 459/456/403/399/331 added lines, all planning documents. No code, no tests.

**Decision.** T2 / LD / **docs** / confidence 4.

**Why.** The trailer makes it T2. Every file is markdown under `.cursor/plans/`, which is documentation, not runtime rules (runtime rules live under `.claude/`, `.cursor/rules/`, or similar). The rule chose `structural` because of the large line count; size is not structure. A docs-only PR is `docs`, regardless of how many lines it adds.

**What would change it.** If the files were `.cursor/rules/*.mdc` loaded by the agent at runtime, the layer would be L2 and the type could be additive. Planning documents are not runtime configuration.

---

## How to use these examples in the app

1. Open `review.html`, jump to the record id (the id is in the header).
2. Expand **Why the rule said this** and **Diff excerpt**.
3. Make your own decision first; then compare with the table above.
4. For E6–E10, select **disagree** and the corrected value, and copy the one-line reason into notes. The reason should cite a file or hunk, not just restate the label.

If your judgment differs from an example, do not force agreement. Record what you see and explain it; the adjudicator will resolve it against the codebook.
