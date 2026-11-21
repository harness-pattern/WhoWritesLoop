# Phase 1 / 交付物 C：打标规范（Labeling Specification v1.0）

> 目标：让 Tier 归因与架构分层**可复现、可审计、可计算一致性**。
> 所有规则同时实现为代码（`pipeline/rules.py`），本文件是代码的规范来源；两者不一致时以本文件为准并修代码。

---

## 1. Tier 归因规范

### 1.1 判定顺序

对每个 PR 依次判定，**首次命中即停**：

```
IF 作者是依赖/发布机器人            → EXCLUDED（不入样）
ELIF 作者是 Agent 机器人             → Tier 1
ELIF 正文/提交含「端到端自主生成」声明 → Tier 1
ELIF 正文/提交含协作标记              → Tier 2
ELSE                                → Tier 3
```

Tier 1 优先于 Tier 2：如果 PR 由 `copilot-swe-agent[bot]` 发起、人类在 commit 里加了 `Co-authored-by`，仍记 Tier 1（人类是 review 者，不是共同作者）。

### 1.2 Tier 1：Autonomous Agent PR

**账号级证据**（`author.type == "Bot"` 且 login 命中下表，大小写不敏感）：

| 账号模式 | 对应 Agent |
|---|---|
| `copilot-swe-agent[bot]`、`copilot[bot]`（仅当 PR 含代码变更） | GitHub Copilot Workspace / Coding Agent |
| `devin-ai-integration[bot]`、`devin[bot]` | Devin |
| `swe-agent[bot]`、`sweagent[bot]` | SWE-agent 自托管 |
| `openhands-agent[bot]`、`openhands[bot]` | OpenHands |
| `google-labs-jules[bot]`、`jules[bot]` | Jules |
| `codegen-sh[bot]`、`codegen[bot]` | Codegen |
| `cursor[bot]`、`cursor-agent[bot]` | Cursor Background Agent |
| `claude[bot]`、`claude-code[bot]` | Claude Code（仅当 PR 含代码变更） |
| `aider[bot]`、`aider-agent[bot]` | Aider |
| `codex[bot]`、`openai-codex[bot]` | Codex |
| `gemini-cli[bot]`、`gemini-agent[bot]` | Gemini CLI |

**文本级证据**（作者是 Human，但 PR 明确声明端到端自主）：

- 正文匹配 `(?i)(fully|entirely|end-to-end)\s+(autonomous|automated|generated)\s+by\s+(an?\s+)?(ai|agent|bot)`
- 正文匹配 `(?i)this\s+pr\s+was\s+(created|generated|authored)\s+(entirely\s+)?by\s+(an?\s+)?(ai|agent)`
- 正文匹配 `(?i)no\s+human\s+(code\s+)?(was\s+)?(written|authored)`

**保守原则**：文本级证据容易造假或误用（例如人类写了 PR 描述说“AI generated”但实际上手改了 80%）。因此文本级 Tier 1 需同时满足：① 匹配上述强声明；② 无人类 `Co-authored-by` 以外的共同作者；③ 该 PR 的 `author_association` 为 `NONE` 或 `CONTRIBUTOR`（排除维护者自述）。不满足则降为 Tier 2。

### 1.3 Tier 2：Co-authored / Assisted

命中任一即 Tier 2：

**提交 trailer**（对所有 commit message 做正则）：
```
(?i)^co-authored-by:\s*.*(claude|anthropic|copilot|github copilot|devin|cursor|aider|codex|openai|gemini|windsurf|bolt|replit)
(?i)^made-with:\s*(cursor|claude|codex|aider)
(?i)^generated-by:\s*(claude|codex|aider|cursor)
```

**PR 正文/评论中的工具签名**：
```
(?i)generated\s+with\s+\[?claude\s+code
(?i)🤖\s*generated\s+with
(?i)co-authored-by:\s*(claude|devin|copilot|cursor|aider|codex)
(?i)aider\s+wrote\s+\d+%?\s+of\s+the\s+code
(?i)this\s+(pr|change|commit)\s+was\s+(written|implemented|assisted)\s+(with|by)\s+(claude|codex|copilot|cursor|aider|devin|gemini)
(?i)ai[- ]assisted
```

**PR 模板字段**：若正文含结构化字段且值为肯定，如
`AI[- ]?(assisted|generated)\s*[:：]\s*(yes|true|✅)`。

**注意**：`Co-authored-by: dependabot` 不算 Tier 2（那是依赖机器人）；`Signed-off-by` 不算（法律声明）。

### 1.4 Tier 3：Human-attributed baseline

无上述任何标记。**定义措辞**：报告中一律写“无显性 Agent 声明的基线组”，不写“纯人类编写”。这是本研究最重要的效度声明。

### 1.5 Agent 身份归一化

Tier 1/2 都要输出 `agent_family`：

| agent_family | 证据关键词 |
|---|---|
| `claude_code` | claude, anthropic, claude code |
| `github_copilot` | copilot |
| `devin` | devin |
| `cursor` | cursor |
| `aider` | aider |
| `codex` | codex, openai codex |
| `gemini_cli` | gemini |
| `openhands` | openhands |
| `swe_agent` | swe-agent, sweagent |
| `jules` | jules |
| `codegen` | codegen |
| `other_bot` | 其他 Bot 账号 |

一个 PR 可能有多个 Agent 署名 → `agent_family` 取**首个命中的强证据**（账号 > trailer > 正文），并在 `agent_families_all` 保留全部。

### 1.6 已知误判与处理

| 情形 | 处理 |
|---|---|
| 维护者用 `claude[bot]` 做 issue 分类，非代码 PR | 要求 `changed_files ≥ 1` 且存在非文档代码文件，否则 EXCLUDED |
| Bot 提 PR 但人类重写了大部分 | 仍记 Tier 1（归因看发起与控制权），但在 `human_rewrite_suspect` 标记：人类在该 PR 上的 commit 数 ≥ Bot commit 数 |
| `Co-authored-by` 被模板自动加在所有 commit | 若仓库 >80% 的 PR 都含该 trailer，则该仓库的 Tier 2 标记失效，改用 PR 正文显式声明；报告中单列该仓库 |
| squash merge 丢失 trailer | 抓取 `PR.commits` 而非仅 merge commit；若仍丢失，记录 `trailer_missing_risk` |

---

## 2. 架构分层打标规范

### 2.1 规则层（全量）

输入：PR 的文件列表（路径 + 状态 + 增删行）。按 `02_taxonomy.md` §2 优先级映射，输出：

```json
{
  "layers": {"L1": 120, "L3": 40, "L4": 12},
  "layers_by_files": {"L1": 3, "L3": 2, "L4": 1},
  "unclassified_files": 0,
  "layers_touched": 3,
  "touches_core": true,
  "core_share": 0.63,
  "test_share": 0.07,
  "docs_only": false
}
```

行数加权用 `additions + deletions`；二进制/锁文件按 0 行计但保留文件计数。

### 2.2 变更类型（全量初判 + 抽样复核）

按 `02_taxonomy.md` §5.2。规则输出 `change_type_rule` 与 `change_type_confidence`（high/medium/low）。低置信度进入 LLM 复核池。

### 2.3 LLM-as-a-Judge（分层抽样）

**抽样框**：按 `repo × tier × quarter` 分层，每层最多 40 条，总预算 1,500 条；Tier 1 全量纳入（通常量小），Tier 2/3 随机抽样。若 Tier 1 不足 200 条，则 Tier 1 全量 + Tier 2/3 补足。

**输入构造**（控制 token）：
1. PR 标题（全文）
2. 正文前 2,000 字符（去除模板噪音、复选框）
3. 文件清单：路径 + `+adds/-dels`，最多 60 个文件，超出按变更量取 top 60
4. 提交信息前 20 条（每条截断 200 字符）
5. Diff 片段：仅当规则层置信度低或 PR 触及 L1 时附加，按文件取前 3 个、每文件 80 行

**输出 JSON Schema**（强制）：
```json
{
  "layers": ["L1", "L3"],
  "primary_layer": "L1",
  "change_type": "structural|additive|fix|docs|test_only|ui",
  "touches_core_loop": true,
  "cross_cutting": true,
  "abstraction_vs_patch": "abstraction|mixed|conditional_patch|unclear",
  "evidence": "一句话，引用具体文件或代码结构",
  "confidence": 0.0
}
```

**判定要点写进 Prompt**（节选）：
- “L1 指改变 Agent 决策序列的代码：循环、状态机、调度、重试、终止条件。仅仅**调用** core 的 UI 代码不算 L1。”
- “`abstraction` 指引入新接口/基类/策略对象来消除分支；`conditional_patch` 指在同一函数里加 if/else 或特判来绕过问题。两者都可能修好 bug，但架构后果不同。”
- “若 PR 同时修改测试与实现，以实现的层为准，测试只作为 L4 的附加标签。”
- “不确定时输出 `unclear` 并给低置信度，不要猜。”

**温度 0，单次调用，不做 self-consistency**（成本考虑）；对 5% 样本做二次调用测稳定性。

### 2.4 人工校准（专家裁决）

- 抽样：150 条，按 `repo × tier` 分层，Tier 1 过采样（占 40%），因为 Tier 1 是核心结论。
- 盲标：裁决者只看 PR 内容，不看规则/LLM 输出。
- 指标：
  - Tier 三分类：Cohen's κ（规则 vs 裁决）
  - 架构层多标签：按文件加权的 Jaccard 均值 + 每层 κ
  - 变更类型：κ
  - `abstraction_vs_patch`：κ（仅 LLM 子样本）
- 验收：Tier κ ≥ 0.80，层 κ ≥ 0.65，变更类型 κ ≥ 0.60。未达标则修订规则并重跑，不允许“调参到达标”式循环——最多两轮，第二轮结果无论好坏都报告。

> **诚实声明**：本研究的“人工校准”由研究助手（LLM）在阅读 PR 全文 diff 后裁决，并非独立人类双标。这在方法上弱于双人盲标，因此：① 裁决记录全部留痕（`data/calibration/`），供真实人工复核；② 报告中把 κ 解释为“规则与专家裁决的一致性”，不外推为“与人类群体的一致性”。

---

## 3. 数据质量闸门

每个阶段设硬闸门，不通过不进入下一阶段：

| 闸门 | 指标 | 阈值 |
|---|---|---|
| G1 抓取完整性 | 每个仓库 PR 数与 GitHub 页面 `totalCount` 偏差 | ≤ 1%（分页丢失检测） |
| G2 字段完整性 | `merged_at`、`files`、`commits` 非空率 | ≥ 99% |
| G3 路径覆盖 | 行数加权 UNCLASSIFIED | ≤ 5% |
| G4 Tier 规则 | 与裁决集 κ | ≥ 0.80 |
| G5 层规则 | 与裁决集 κ | ≥ 0.65 |
| G6 Revert 识别 | 人工抽查 30 条 revert 链接 | 准确率 ≥ 90% |
| G7 抽样代表性 | 明细样本与普查在 repo×tier×quarter 上的分布差异 | 总变差距离 ≤ 0.10 |

---

## 4. 分析口径约定（写进最终报告的方法节）

1. **合入率**：`merged / (merged + closed_unmerged)`，排除 cutoff 时仍 open 的 PR。分仓库计算后再汇总（避免大仓库主导）。
2. **返工轮次**：`review_comments + changes_requested_reviews`；同时报告 `time_to_merge` 中位数。
3. **回滚率**：PR 合并后 30 天内被 revert 的比例；revert 识别用 `Revert "..."` 标题 + 正文引用 PR 号 + 文件重叠三路匹配。
4. **仓库内对比优先**：所有 RQ1/RQ2 的主检验用仓库内配对/分层比较（Mantel-Haenszel 或混合效应 logistic），跨仓库汇总只作为描述。
5. **多重比较**：主要假设（≤6 个）用 Benjamini-Hochberg 控制 FDR=0.05；探索性分析标注为 exploratory。
6. **右截断**：2026-09-21 之后创建的 PR 在合入率分析中排除（给 60 天合并窗口），但保留在架构层分析中。
