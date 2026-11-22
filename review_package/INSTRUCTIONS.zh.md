# 评审员手册 —— Harness 挖掘审计（中文版）

版本 1.1 · 2026-11-22 · 配合 `review.html` 与 `codebook.md` 使用

这份文档是 120 条人工复核的操作手册。它说明每一步该看什么、怎么判、遇到边界情况怎么处理，以及你的答案如何变成 Cohen's κ。`EXAMPLES.zh.md` 给出 10 条完整示例，其中 5 条是故意保留的规则错误。

**两种模式。** app 默认是 **annotator 模式**：你直接给 author type、layer、change type 打标签，自动标签默认隐藏。顶部勾选 **显示自动标签（审计模式）** 后会显示规则答案和实时匹配情况；它用于校准，不要用来锚定第一判断。无论哪种模式，导出的 CSV 都会自动生成规则 vs 标注的对比列，分析口径一致。

English version: `INSTRUCTIONS.md`.

---

## 1. 这次审计是什么，不是什么

你要审计的是三个自动化工具：

1. GitHub 挖掘管线：PR 编号、标题、作者、合并状态是否抓对；
2. 归因规则：这条 PR 是自主 Agent、协作/辅助，还是无显式标记；
3. 架构映射：实质性改动落在哪一层，属于哪种变更类型。

你**不是**在评价 PR 写得好不好、Agent 能力强不强、设计是否合理，也不是在验证作者论文的结论。一个质量很差的 PR，仍然可以被正确地标成 T1/L4/fix。

你也不是在给整个语料重新打标。你看到的是 120 条分层抽样；你的 κ 描述的是工具的一致性，不是总体比例。

---

## 2. 开始之前

- 用浏览器打开 `review.html`。样本、证据、codebook、κ 计算器都在文件里，不需要服务器。
- 一个 reviewer 一份表单。Reviewer A 和 Reviewer B 独立填写，互不看对方的表。
- 每条 **2–3 分钟**，120 条约 **4–6 小时**。建议分三次；答案会自动保存在浏览器里。
- 提交前不要看另一位 reviewer 的表。
- 不要问规则作者“这条应该标什么”。可以问 codebook 的解释，不要问答案。
- 刷新或关标签页后，app 会从 `localStorage` 恢复。完成后点 **Export CSV**。

---

## 3. 界面结构

每条记录从上到下是：

| 区块 | 内容 | 用途 |
|---|---|---|
| 头部 | 记录 id、仓库、PR 编号、创建日期、合并状态 | 身份核对 |
| 标题 | 抓取到的 PR 标题 | 身份核对 |
| 元数据 | 作者、association、`+新增/−删除`、文件数、commit 数、review 评论数 | 规模与贡献者类型 |
| 自动标签框（可选） | 规则 tier、规则 layer、规则 change type、全部 layers | 默认隐藏；打开审计模式后用于对比，不要用来锚定 |
| Why the rule said this | 规则名、命中的文本、账号、层权重 | 规则为什么触发 |
| Evidence | PR 正文、文件表（路径、层、状态、增删）、commit 标题 | layer / change type 的主要证据 |
| Diff excerpt | GitHub diff 的前 7 KB | change type 和边界层的关键证据 |
| 问题 1–5 | 身份、tier、layer、change type、confidence/notes | 你的输出 |
| Unreviewable | 勾选框 | 只有确实无法判断时才用 |
| Agreement | 浏览器内 κ | 进度检查 |

自动标签默认隐藏。先给出你自己的标签；需要时再打开 **显示自动标签（审计模式）** 看规则答案和是否匹配。导出会自动生成对比列，不需要你手动把“同意/不同意”翻译成标签。

---

## 4. 六个判定字段

每条记录输出：

1. `title_matches` — Y/N
2. `merge_status_matches` — Y/N
3. `tier_annotator` — T1 / T2 / T3（谁写的）
4. `layer_annotator` — L1 / L2 / L3 / L4 / L0 / LD（改了哪一部分）
5. `change_type_annotator` — structural / additive / fix / test_only / docs / ui（哪种改动）
6. `confidence_1_5`、`notes`；可选 `unreviewable`

你只负责给标签；app 会在后台与规则比较，并在导出时写出 `tier_correct`、`tier_corrected` 等列。五个判断都填了，或勾了 unreviewable，这条才算完成。

---

## 5. 判定规则

### 5.1 身份核对

打开 GitHub 链接，核对三件事：

- URL 里的 PR 编号等于记录的 `pr_number`；
- GitHub 上的标题等于内嵌标题（空白和大小写差异可忽略）；
- 合并状态一致：`merged`、`closed-unmerged`、`open`。

如果 PR 或仓库已删除：勾 `unreviewable`，写明原因。如果标题在抓取后被编辑，但编号和合并状态正确：`title_matches=N`，note 写“标题在抓取后被编辑”，不要因此把整条标成不可评审。

### 5.2 Tier

按顺序命中第一条。

**测试 1 —— bot 账号。** login 以 `[bot]` 结尾，或 GitHub 页面标明是 bot/app，或 login 在已知自动化名单里（`copilot-swe-agent`、`devin-ai-integration`、`opencode-agent`、`cline-cloud`、`continue`、`cursor`、`codegen-sh`、`google-labs-jules`、`swe-agent`、`aider`、`gemini-cli`、`cubic-dev-ai`、`hf-security-analysis`、`blacksmith-sh`、`ellipsis-dev`）。→ **T1**。

**测试 2 —— 显式自主声明。** 正文明确说这次改动由 AI 端到端生成、没有人类作者，例如 “This PR was created entirely by an AI agent”、“no human code was written”。→ **T1**。

**测试 3 —— 正向协作证据。** commit trailer（`Co-Authored-By: Claude`、`Co-authored-by: Cursor`、`Made-with: Cursor`）、工具签名（`Generated with [Claude Code]`、`aider wrote 62% of the code`），或结构化的 `AI-assisted: yes` 字段。→ **T2**。

**测试 4 —— 以上都没有。** → **T3**，无显式声明基线。

关键区分：

- **人类用 GitHub App token 提交，不等于 T1。** 如果页面显示的是人、login 没有 `[bot]`，即使 API 报 `type=Bot`，也按人处理；没有 trailer 就是 T3。
- **只做镜像的 bot 不是 Agent。** Copybara/Copyberry、依赖/发布 bot 在抽样前已被排除。若漏进来，标 `tier_correct=N`，note 写“excluded bot leaked into sample”。
- **正文里说“我用了 Copilot”不算 T2。** 只有 trailer、工具签名或结构化字段才算。
- **人类重写了 Agent PR 的大部分内容，仍然是 T1。** 归因看发起与控制权，不看行数。
- **bot 提的纯文档 PR 仍然是 T1。** Tier 看作者身份，不看层。不要因为改动琐碎就把 T1 改成 T3。

### 5.3 Layer

先判断是不是 **test-only** 或 **docs-only**：

- 所有改动文件都是测试/fixture/benchmark → **L4**，change type `test_only`。
- 所有改动文件都是文档（`.md`、docs 站、README、changelog）→ **LD**，change type `docs`。例外：`.claude/`、`.clinerules/`、`.agents/`、`.gemini/`、`.roo/`、`queries/`、`prompts/` 是运行时规则/提示词 → **L2**。

如果实现与测试/文档混合，**选择 primary layer 时忽略测试、文档和生成文件**。1 行 UI 改动配 300 行测试，primary layer 是 **L0**，不是 L4。这是样本里最常见的规则错误。

然后在实现文件里按实质性行数选 **primary layer**：

| 层 | 内容 | 典型路径 |
|---|---|---|
| **L1** 核心循环 | turn loop、状态机、任务/子 Agent 调度、规划/反思、重试/回退、终止条件、并发模型 | `core/controller`、`core/task`、`core/loop`、`session`、`machine`、作为 runner 的 `agent` |
| **L2** 上下文与记忆 | system prompt、工具**描述**、压缩/截断、RAG/索引、会话持久化、规则/skills、配置加载 | `core/prompts`、`context`、`memory`、`skills`、`config`、prompt 目录下的 `*.md` |
| **L3** 工具与沙箱 | 工具实现、MCP、shell/browser/file 执行器、patch 应用、权限、沙箱、provider 适配、外部协议 | `tools`、`mcp`、`sandbox`、`providers`、`llm`、`api`、`runtime` |
| **L4** 评测与基建 | 测试、benchmark、CI、遥测、trace、构建脚本、lint/类型配置 | `test`、`__tests__`、`.github/`、`Dockerfile`、`pyproject.toml` |
| **L0** 产品表面 | webview/UI、TUI 渲染、桌面壳、官网、示例、i18n | `webview-ui`、`gui`、`packages/ui`、`components`、`*.tsx`、`*.css` |
| **LD** 文档 | README、docs 站、changelog、纯注释 markdown | `docs/`、`README`、`CHANGELOG` |

Tie-break：

1. 混合 PR 里，测试/文档/生成文件永远不决定 primary layer。
2. 两个实现层行数相同，优先编号更小的层（L1 > L2 > L3 > L4 > L0 > LD）。
3. 改动 loop 使用的共享类型 → **L1**；模型目录或 provider 类型条目 → **L3**，即使它在 `types/` 包下。
4. 提示词/工具描述文件 → **L2**（上下文），不是 L3（工具实现）。真正执行工具的代码是 L3。
5. skills 刷新 controller（`refreshSkills.ts`）→ **L2**，不是 L1，即使它在 `src/core/controller/` 下。它管理 skills，不管理 loop。
6. UI 组件里的安全修复 → **L0**；执行器/工具层的安全修复 → **L3**；改变 loop 授权契约的安全修复 → **L1**。

### 5.4 Change type

按顺序判断：

1. **test_only** —— 只改测试/fixture/benchmark。
2. **docs** —— 只改文档。
3. **ui** —— 只改产品表面文件（可附带测试）。
4. **structural** —— 重构核心循环、改变接口/基类/契约、改变并发或安全模型，或跨层且有大量删除/重命名。至少满足一项：核心层且删除比 > 0.3；重命名/删除接口文件；≥2 个 harness 层且 ≥10 个文件；标题含 refactor/migrate/rewrite **且** diff 确实有结构变化。
5. **additive** —— 新增文件/适配器/工具/测试/提示词，删除很少，没有核心重写。
6. **fix** —— bug、崩溃、回归、兼容性修复，且不是结构性。

`structural` 不等于“大”。新增 500 行模型目录是 **additive**；删除 30 行、但改掉了任务 controller 使用的接口，可能是 **structural**。只改版本常量的兼容性升级是 **fix**。

### 5.5 Confidence

| 分数 | 锚点 |
|---|---|
| 5 | diff 和 GitHub 页面都无歧义，另一位 reviewer 会得出同样标签。 |
| 4 | 清楚，但有一个小歧义（例如 UI 修复附带测试）。 |
| 3 | primary layer 依赖判断（共享类型、prompt vs tool、controller vs loop）。 |
| 2 | diff 被截断、PR 混合多个关注点、文件大量重命名。 |
| 1 | 你在猜；在 notes 里说明。 |

不要为了“好看”抬高 confidence。一个自信的 5 分错误，比诚实的 2 分更有害。

### 5.6 Unreviewable

只在以下情况勾选：

- 仓库或 PR 已删除，且没有可用文件清单；
- patch 为空 **且** 文件清单缺失/不可读；
- 这条记录与另一条重复（note 写重复 id）。

仅仅“diff 为空”**不够**：如果文件清单和 commit 标题在，就根据它们判断，note 写“no diff; judged from file list”。本样本有 4 条 diff 为空，但仍然可以判断。

---

## 6. 硬案例矩阵

| 情形 | 判定 | 理由 |
|---|---|---|
| bot 提纯文档 PR | T1, LD, docs | tier 看作者，layer 看文档 |
| 人类用 Cursor 但无 trailer | T3 | 没有正向证据 |
| 人类 + `Co-Authored-By: Claude` | T2 | trailer 就是证据 |
| `cline-cloud[bot]` 删除核心 loader | T1, L1, structural | bot；`core/task` 删除 355 行；共享 tools 契约变化 |
| `roo-code-cte[bot]` 新增 provider 模型 | T1, **L3**, additive | provider 目录，不是 loop；`types/providers` 属于 L3 |
| `copilot-swe-agent` 只改一个测试 | T1, L4, **test_only** | test-only；标题写 fix 也不改变类型 |
| `opencode-agent` 修 TUI（1 行产品 + 34 行测试） | T1, **L0**, ui（或 fix） | 测试不决定 primary layer |
| `Co-Authored-By: Claude` 重构 `refreshSkills.ts` | T2, **L2**, structural | skills 属于上下文/记忆，不是 L1 |
| PR 只有 `.cursor/plans/*.md` | T2, LD, **docs** | 规划 markdown 是文档 |
| PR 混合 3 个 docs + 2 个 CI workflow | L4, additive/fix | CI 是基建；docs 不决定层 |
| 只改 `package-lock.json` | GEN，排除 | 生成/锁文件不在词表内 |
| 标题写 refactor，diff 只是 3 行重命名 | fix 或 additive | structural 需要真实结构变化 |

---

## 7. 完整示例

`EXAMPLES.zh.md` 用当前样本里的 10 条真实记录，列出内嵌文件、diff 摘要、正确答案和理由。**E6–E10 是故意的规则错误**，表中“正确答案”是你应该选的标签，不用管自动标签说了什么。开始前至少读 E1–E5。

快速索引：

| 示例 | 记录 | 规则 | 正确答案 | 教训 |
|---|---|---|---|---|
| E1 | S012 | T1/LD/docs | 一致 | 显式 AI 声明让人类账号成为 T1 |
| E2 | S001 | T3/L2/fix | 一致 | 工具描述属于 L2 |
| E3 | S003 | T2/L3/additive | 一致 | co-author trailer + 新工具 |
| E4 | S016 | T1/L1/structural | 一致 | `core/task` 删除是核心 |
| E5 | S015 | T1/L0/ui | 一致 | 只有 CSS/TSX |
| E6 | S026 | T1/L4/fix | **test_only** | 标题 fix ≠ 代码修复 |
| E7 | S002 | T1/L1/additive | **L3** | provider 目录不是 loop |
| E8 | S014 | T1/L4/fix | **L0** | 测试不决定 primary layer |
| E9 | S022 | T2/L1/structural | **L2** | skills loader 是上下文 |
| E10 | S046 | T2/LD/structural | **docs** | 规划 markdown 不是结构代码 |

---

## 8. 双 reviewer 流程

1. **Reviewer A** 和 **Reviewer B** 独立审同样的 120 条，互不看表。
2. 导出 `review_form_filled_A.csv`、`review_form_filled_B.csv`。
3. 分别计算：

```bash
python3 compute_agreement.py --form review_form_filled_A.csv --out agreement_A.md
python3 compute_agreement.py --form review_form_filled_B.csv --out agreement_B.md
```

4. **Adjudicator** 打开 A/B 不一致的行，读同一份内嵌证据，写 `review_form_adjudicated.csv`。裁决者可以查 codebook，但不能问规则作者的“本意”。
5. 同时报告 A、B 和裁决后的 κ。不要只报更好的那个。

如果某个维度没达标，修订 codebook 或规则，用**新 seed 重抽**，再审计。不要在同一批 120 条上反复调参，然后把调出来的 κ 当作独立结果。

---

## 9. 导出与一致性报告

HTML 导出的 `review_form_filled.csv` 列：

```
id, reviewer, review_date, title_matches, merge_status_matches,
tier_annotator, layer_annotator, change_type_annotator,
tier_correct, tier_corrected, layer_correct, layer_corrected,
change_type_correct, change_type_corrected, confidence_1_5,
unreviewable, notes
```

`*_annotator` 是你选的标签；`*_correct` 和 `*_corrected` 是 app/脚本自动推导的对比列，因此 annotator 与 audit 两种流程共用同一份分析文件。

运行：

```bash
python3 compute_agreement.py \
  --form review_form_filled.csv \
  --sample review_sample.csv \
  --counts repo_counts.csv
```

输出 `agreement_report.md` 和 `agreement_summary.json`，包含 accuracy、κ、最常见的 rule→human 修正、平均 confidence、仓库计数偏差。

阈值：tier κ ≥ 0.80，layer κ ≥ 0.65，change type κ ≥ 0.60，identity 100%，仓库计数偏差 ≤ 1%。

---

## 10. 常见错误

1. **让测试决定层。** 只有 test-only PR 才是 L4；混合 PR 由实现决定。
2. **把标题里的 fix 当成 change type。** test-only fix 是 `test_only`；兼容性升级是 `fix`；契约重写是 `structural`。
3. **把所有 `types/` 改动当 L1。** provider 目录和 model ID 是 L3。
4. **把所有 `core/` 路径当 L1。** `core/prompts` 是 L2，`core/util` 通常是 L4，`core/controller/file/refreshSkills` 是 L2。
5. **把 bot 的文档 PR 当 T3。** tier 看作者。
6. **diff 缺失就标 unreviewable。** 有文件和 commit 就判断，并注明局限。
7. **判断性边界给 5 分。** 真正有争议时用 3。
8. **disagree 不写 note。** 每个 N 都要一句理由，引用文件或 hunk。
9. **回头改答案去迎合规则。** 记录第一判断；不一致本身就是数据。
10. **只报一个 reviewer。** 流程需要 A、B 和裁决文件。

---

## 11. 时间安排

| 场次 | 记录 | 重点 |
|---|---|---|
| 1（90 分钟） | S001–S040 | 读 codebook；先做 5 个示例；会慢 |
| 2（90 分钟） | S041–S080 | 稳定节奏；注意 test-heavy 和 provider PR |
| 3（90 分钟） | S081–S120 | 收尾；导出；跑 agreement |
| 裁决（60 分钟） | 不一致记录 | A + B + adjudicator |

如果进度落后，不要省 notes。小批量但完整的记录，比 120 条草率记录更有用。

---

## 附录：字段参考

| 字段 | 允许值 | 含义 |
|---|---|---|
| `title_matches` | Y / N | GitHub 标题与内嵌标题一致 |
| `merge_status_matches` | Y / N | merged / closed-unmerged / open 一致 |
| `tier_correct` | Y / N | 规则 tier 正确 |
| `tier_corrected` | T1 / T2 / T3 | `tier_correct=N` 时必填 |
| `layer_correct` | Y / N | 规则 primary layer 正确 |
| `layer_corrected` | L1 / L2 / L3 / L4 / L0 / LD | `layer_correct=N` 时必填 |
| `change_type_correct` | Y / N | 规则 change type 正确 |
| `change_type_corrected` | structural / additive / fix / docs / test_only / ui | `change_type_correct=N` 时必填 |
| `confidence_1_5` | 1–5 | 见 §5.5 |
| `unreviewable` | Y / 空 | 只在 §5.6 情况下使用 |
| `notes` | 自由文本 | 每个 N 和 unreviewable 都必须写 |
