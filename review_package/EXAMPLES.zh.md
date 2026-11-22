# 完整示例 —— Harness 挖掘审计（中文版）

10 条来自当前 120 条样本的真实记录。每条列出内嵌证据、判定、理由，以及“什么情况下答案会变”。**E6–E10 是故意保留的规则错误**：它们教你区分“规则触发了”和“规则是对的”。开始前先读 E1–E5，再做正式评审；E6–E10 留到裁决阶段对照。

在 `review.html` 里按 id 打开同一条记录，可以看到完整证据和 diff。English version: `EXAMPLES.md`.

| # | 记录 | 规则 | 正确答案 | 结论 | 教训 |
|---|---|---|---|---|---|
| E1 | S012 | T1 / LD / docs | 相同 | 同意 | 显式 AI 声明让人类账号成为 T1 |
| E2 | S001 | T3 / L2 / fix | 相同 | 同意 | prompt/工具描述文件属于 L2 |
| E3 | S003 | T2 / L3 / additive | 相同 | 同意 | co-author trailer + 新工具 |
| E4 | S016 | T1 / L1 / structural | 相同 | 同意 | `core/task` 删除属于核心 |
| E5 | S015 | T1 / L0 / ui | 相同 | 同意 | 只有 CSS/TSX |
| E6 | S026 | T1 / L4 / fix | T1 / L4 / **test_only** | 不同意 | test-only 的 fix 不是代码修复 |
| E7 | S002 | T1 / L1 / additive | T1 / **L3** / additive | 不同意 | provider 目录是 L3 |
| E8 | S014 | T1 / L4 / fix | T1 / **L0** / **ui** | 不同意 | 测试不决定 primary layer |
| E9 | S022 | T2 / L1 / structural | T2 / **L2** / structural | 不同意 | skills loader 是上下文，不是 loop |
| E10 | S046 | T2 / LD / structural | T2 / LD / **docs** | 不同意 | 规划 markdown 不是结构代码 |

---

## E1 —— S012 · OpenHands/software-agent-sdk #2952

**规则：** T1 / LD / docs —— **同意**。

**记录显示什么。** 作者 `smolpaws`（看起来是人类 login），association `CONTRIBUTOR`。PR 正文有一句明确声明：“This PR was created by an AI”。文件只有 `README.md`，新增 2 行、删除 1 行。diff 在安装章节加了一句“For local development from this repository, run `make build`…”，并更新了一个文档链接。

**判定。**

| 字段 | 值 |
|---|---|
| 标题 / 合并 | Y / Y（merged） |
| Tier | T1 |
| Layer | LD |
| Change type | docs |
| Confidence | 5 |

**为什么。** Tier 看作者身份，不看层：作者是人类，但正文是正向的端到端自主声明，命中 T1 的测试 2。唯一文件是 `README.md`，所以 layer 是 LD、类型是 docs。bot 或 AI 写一行 README，仍然是 T1/LD/docs。

**什么会改变答案。** 如果证据是 co-author trailer 而不是显式声明，就是 T2。如果 diff 里出现代码文件，层会变化；文档不决定混合 PR 的层。

---

## E2 —— S001 · RooCodeInc/Roo-Code #6877

**规则：** T3 / L2 / fix —— **同意**。

**记录显示什么。** 作者 `Hannes Rudolph`，association `NONE`，四个 commit（`Update codebase-search.ts`、`fix: make search_files path parameter optional…` 等）里没有 trailer 或工具签名。文件：

```
L2  MODIFIED  11/7   src/core/prompts/tools/codebase-search.ts
L2  MODIFIED   1/1   src/core/prompts/tools/index.ts
```

diff 修改工具描述字符串：给 `getCodebaseSearchDescription` 增加 `ToolArgs` 参数，重写 `codebase_search` 的描述，并说明 `path` 参数是可选的。没有执行器、没有 loop、没有测试。

**判定。** T3 / L2 / fix / confidence 5。

**为什么。** 没有 bot 账号、没有正向证据 → T3。改动在工具的**描述**，不在工具实现，所以是上下文（L2），不是 L3。它修正了误导性的工具说明和参数签名，所以是 `fix`；不是契约重写。

**什么会改变答案。** 如果 diff 同时改了 `src/core/tools/codebaseSearch.ts`（执行器），L3 会参与竞争，并可能按行数胜出。如果作者有 `Co-Authored-By: Claude` trailer，tier 变成 T2。

---

## E3 —— S003 · SWE-agent/mini-swe-agent #770

**规则：** T2 / L3 / additive —— **同意**。

**记录显示什么。** 作者 `DhruvBhatia0`，tier 证据 `{"rule":"coauthor_trailer","match":"Co-Authored-By: Claude"}`。新增文件：

```
L3  ADDED  174  src/minisweagent/models/utils/warpgrep.py
L4  ADDED  144  tests/test_warpgrep.py
L3  ADDED   83  src/minisweagent/models/litellm_warpgrep.py
L2  ADDED   44  src/minisweagent/config/warpgrep.yaml
L3  MODIFIED 1  src/minisweagent/models/__init__.py
```

diff 新增一个 WarpGrep 代码搜索模型适配器及其配置，没有删除既有代码。

**判定。** T2 / L3 / additive / confidence 5。

**为什么。** trailer 是正向协作证据 → T2。主要实现层是 L3（适配器 + registry，共 258 行），L2 配置和 L4 测试是支撑。改动是新增适配器而非重写 → additive。

**什么会改变答案。** 如果它替换了现有搜索后端并删除其接口，`structural` 才成立。只改配置的 PR 会是 L2/additive。

---

## E4 —— S016 · cline/cline #14881

**规则：** T1 / L1 / structural —— **同意**。

**记录显示什么。** 作者 `cline-cloud`（bot）。PR 删除未使用的 `AgentConfigLoader` 及其 `SubagentToolName`，并更新共享工具注册表：

```
L1  DELETED  0/355  apps/vscode/src/core/task/tools/subagent/AgentConfigLoader.ts
L4  ADDED   63/0    apps/vscode/src/core/storage/StateManager.test.ts
L1  DELETED  0/41   apps/vscode/src/core/task/tools/subagent/SubagentToolName.ts
L1  MODIFIED 0/6    apps/vscode/src/shared/tools.ts
L2  MODIFIED 0/3    apps/vscode/src/core/storage/StateManager.ts
```

**判定。** T1 / L1 / structural / confidence 5。

**为什么。** bot 账号 → T1。实现部分由 `core/task/tools/subagent` 的 L1 删除主导，并修改共享工具契约，所以是 L1。删除 loader 及其导出类型改变 sub-agent 工具接线，这是结构性，不是 additive，即使 PR 标题只是“cleanup”。63 行测试是支撑，不改变层。

**什么会改变答案。** 如果 loader 仍被引用、PR 只是移除一个未使用 export，可能是 `additive` 或 `fix`。删除 355 行类并修改 `tools.ts` 才让它成为 structural。

---

## E5 —— S015 · anomalyco/opencode #45486

**规则：** T1 / L0 / ui —— **同意**。

**记录显示什么。** 作者 `opencode-agent`（bot）。三个产品表面文件：

```
L0  MODIFIED  5/0  packages/session-ui/src/components/message-part.css
L0  MODIFIED  2/1  packages/app/src/session/timeline/virtualizer.tsx
L0  MODIFIED  1/0  packages/app/src/session/timeline/message-timeline.tsx
```

diff 把 `workspaceSession` 传入 `VirtualizedTimeline`，并调整消息强调色 CSS。

**判定。** T1 / L0 / ui / confidence 5。

**为什么。** 所有实现文件都是 UI/session 表面，没有碰 harness 层。`ui` 是正确的，因为这是产品呈现而非 harness 修复。bot 只改 CSS 仍然是 T1。

**什么会改变答案。** 如果改动改变 session 状态语义而非呈现，L2 会参与竞争。如果修的是 virtualizer 崩溃，`fix` 也说得通；内嵌 diff 显示是 prop/CSS 改动，所以 `ui` 更合适。

---

## E6 —— S026 · QwenLM/qwen-code #3784

**规则：** T1 / L4 / fix —— **change type 不同意**。

**记录显示什么。** 作者 `copilot-swe-agent`（bot）。唯一改动文件是测试：

```
L4  MODIFIED  15/18  packages/core/src/tools/monitor.test.ts
```

diff 在 Windows 下给 `taskkill` 断言补上缺失的 `stdio` 选项。

**判定。** T1 / L4 / **test_only** / confidence 5。

**为什么。** bot → T1；唯一文件是测试 → L4。但它修的是**测试断言**，不是生产行为。标题写“fix”导致规则选了 `fix`；分类体系里 `test_only` 更具体、优先级更高。这是干净的 disagree：`change_type_correct=N`，corrected `test_only`，note 写“only `monitor.test.ts` changed”。

**什么会改变答案。** 如果同时改了 `monitor.ts` 的生产代码，就是 `fix`，层会变成 L4/L3 混合。新增测试文件但无行为变化，仍是 `test_only`。

---

## E7 —— S002 · RooCodeInc/Roo-Code #8655

**规则：** T1 / L1 / additive —— **layer 不同意**。

**记录显示什么。** 作者 `roo-code-cte`（bot）。文件：

```
L1  MODIFIED  20/6  packages/types/src/providers/chutes.ts
L4  MODIFIED  22/0  src/api/providers/__tests__/chutes.spec.ts
```

diff 给 `ChutesModelId` union 增加 `"inclusionAI/Ring-1T-FP8"`，并补 provider 测试。

**判定。** T1 / **L3** / additive / confidence 4。

**为什么。** 规则把 `packages/types/**` 映射到 L1，因为共享类型可能是契约。但这个文件是 **provider 模型目录**——某个 provider 适配器暴露的 model ID 列表，属于 provider 层（L3），不是 agent loop。测试是支撑，不决定层。新增一个 model entry → additive。

**什么会改变答案。** 如果 PR 改的是任务 controller 使用的 `AgentConfig` 类型，L1 才对。不能只看路径，要读类型本身。

---

## E8 —— S014 · anomalyco/opencode #37674

**规则：** T1 / L4 / fix —— **layer 和 type 都不同意**。

**记录显示什么。** 作者 `opencode-agent`（bot）。文件：

```
L4  MODIFIED  34/2  packages/tui/test/cli/tui/dialog-select.test.tsx
L0  MODIFIED   1/1  packages/tui/src/ui/dialog-select.tsx
```

产品改动在对话框 focus 条件里加了 `&& store.input !== "mouse"`；其余是鼠标选择的回归测试。

**判定。** T1 / **L0** / **ui** / confidence 4。

**为什么。** 规则把 34 行测试算成 L4，让它压过 1 行产品改动。这是典型的 test-heavy 错误：测试支撑改动，但不定义改动所在的层。实质变化是 TUI 行为修复，所以 L0。类型选 `ui`，因为只有产品表面实现变化（外加测试）；把它读成 bug fix 而选 `fix` 也说得通，但分类体系里 `ui` 对“纯呈现改动”更具体。

**什么会改变答案。** 如果改动改变对话框**状态语义**并被 session 层使用，L2 会参与竞争。如果修的是共享组件崩溃，`fix` 更合适。

---

## E9 —— S022 · cline/cline #9956

**规则：** T2 / L1 / structural —— **layer 不同意**。

**记录显示什么。** 作者 `johnwschoi`，tier 证据 `{"rule":"coauthor_trailer","match":"Co-Authored-By: Claude"}`。一个文件：

```
L1  MODIFIED  7/30  src/core/controller/file/refreshSkills.ts
```

diff 删除手写 YAML frontmatter 解析器，改用共享的 `parseYamlFrontmatter`，保持 `RefreshedSkills` 输出不变。

**判定。** T2 / **L2** / structural / confidence 4。

**为什么。** 规则把 `src/core/**` 映射到 L1。但这个文件刷新的是 **skills**——上下文/规则，不是 agent loop。`controller/` 目录只是实现细节，职责属于 L2。改动用一个解析器替换另一个并删了 30 行，所以在 L2 上 `structural` 说得通，即使不是核心层。

**什么会改变答案。** 如果 `refreshSkills` 同时改变 skills 何时/是否进入 prompt 管线，仍是 L2；如果它改变 loop 的工具授权，才是 L1。看调用点，不要只看目录。

---

## E10 —— S046 · aaif-goose/goose #11514

**规则：** T2 / LD / structural —— **change type 不同意**。

**记录显示什么。** 作者 `genarionogueira`，tier 证据 `{"rule":"coauthor_trailer","match":"Co-authored-by: Cursor"}`。没有缓存到 diff（API 返回空），但文件清单完整：五个 `.cursor/plans/*.md`，分别新增 459/456/403/399/331 行，全是规划文档。没有代码、没有测试。

**判定。** T2 / LD / **docs** / confidence 4。

**为什么。** trailer 让它成为 T2。所有文件都是 `.cursor/plans/` 下的 markdown，是文档，不是运行时规则（运行时规则通常在 `.claude/`、`.cursor/rules/` 等目录）。规则因为行数大选了 `structural`；大小不是结构。纯文档 PR 就是 `docs`，不管加了多少行。

**什么会改变答案。** 如果文件是 `.cursor/rules/*.mdc` 且被 agent 运行时加载，层会是 L2，类型可能是 additive。规划文档不是运行时配置。

---

## 在 app 里怎么用这些例子

1. 打开 `review.html`，按 id 跳到记录（header 里有 id）。
2. 展开 **Why the rule said this** 和 **Diff excerpt**。
3. 先自己判，再对照上面的表。
4. 对 E6–E10，选择 **disagree** 和正确值，并把一句理由写进 notes。理由要引用文件或 hunk，不要只重复标签。

如果你的判断和示例不同，不要强行一致。记录你看到的，并解释；裁决者会按 codebook 处理。
