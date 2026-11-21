# Phase 1 / 交付物 A：样本池清单（Sample Pool v2.0，20 仓库）

> 版本：v2.0 ｜ 定稿日期：2026-11-21 ｜ 数据截止：2026-11-20
> v1.0 为 10 仓库；v2.0 依据 POHE 现场指南（harness-pattern.github.io/pohe）给出的 41 仓库面板与规范样本，扩展到 20 个。
> 配套文档：`02_taxonomy.md`（架构分层词表）、`03_labeling_spec.md`（打标规范）

---

## 1. 研究设计与分析单元

**分析单元**：单个 Pull Request（PR）。

**时间窗口**：2025-05-01 00:00 UTC 至 2026-11-20 23:59 UTC，共约 18.6 个月。窗口起点覆盖 Agent 编程工具进入主流工程实践的拐点；终点为抓取日。cutoff 之后创建、截至抓取仍未决的 PR 标记为「观察窗内未决」，不计入合入率分母。

**纳入条件**：

1. 仓库属于下表 20 个样本之一；
2. PR 的 `created_at` 落在窗口内；
3. 目标分支为默认分支，排除向 release/feature 分支的 cherry-pick（同一变更的重复计数）；
4. 排除纯依赖升级与发布机器人 PR，但**保留**由 Agent 执行的依赖迁移与版本适配。

**样本策略**：PR 元数据全量普查；files/commits/reviews 明细按 `repo × tier × quarter` 分层抽 6,000 条（详见 §5）。

---

## 2. 仓库清单（20）

规模列为 2026-11-21 通过 `git ls-remote refs/pull/*/head` 得到的**全历史** PR ref 数，用于判断量级，不是窗口内数量；窗口内实际数量在 `fetch.py list` 后回填。

### 2.1 CLI / Terminal-native（6）

| # | Slug | 语言 | PR refs（全历史） | 最后提交 | 定位与观测重点 |
|---|---|---|---|---|---|
| 1 | `openai/codex` | Rust | 19,496 | 2026-11-20 | 大厂官方 CLI，Rust 系统级代码（并发、TUI、sandbox）；检验 Agent 触碰系统层的边界 |
| 2 | `google-gemini/gemini-cli` | TypeScript | 13,566 | 2026-11-20 | 官方终端 Agent，原生 GitHub 工作流；Dogfooding RSI 的核心样本 |
| 3 | `QwenLM/qwen-code` | TypeScript | 10,595 | 2026-11-21 | Gemini CLI 的下游分叉，高活跃；与 #2 构成“同源分叉”对照，直接检验范式扩散 |
| 4 | `anomalyco/opencode` | TypeScript/Go | 30,029 | 2026-11-20 | 社区头部，PR 吞吐极大；build/plan 双 Agent 与 sub-agent 架构 |
| 5 | `aaif-goose/goose` | Rust/TypeScript | 9,400 | 2026-11-20 | Block 系（现 aaif-goose）CLI + Desktop Agent；Rust 核心 + 多端 UI，检验“核心/界面”分层 |
| 6 | `Aider-AI/aider` | Python | 1,323 | 2026-05-22 | 老牌双模型管线，低频维护；作为“前 Agent 时代”历史基线 |

### 2.2 IDE-integrated / Multi-surface（3）

| # | Slug | 语言 | PR refs | 最后提交 | 定位与观测重点 |
|---|---|---|---|---|---|
| 7 | `cline/cline` | TypeScript | 8,761 | 2026-11-20 | 多端 Monorepo（IDE + CLI + SDK）；Plan/Act、Checkpoints、MCP、Rules/Skills 分层清晰 |
| 8 | `continuedev/continue` | TypeScript | 6,085 | 2026-07-20 | 经典 IDE 扩展生态，贡献者多元；2026-07 后开发放缓，作历史对照 |
| 9 | `RooCodeInc/Roo-Code` | TypeScript | 7,715 | 2026-05-15 | Cline 的知名 Fork，2026-05 归档；分叉后模式互抄与演进分流的天然实验 |

### 2.3 Autonomous / Async SWE（5）

| # | Slug | 语言 | PR refs | 最后提交 | 定位与观测重点 |
|---|---|---|---|---|---|
| 10 | `OpenHands/OpenHands` | Python→TypeScript | 13,264 | 2026-11-21 | 工业级自主 SWE；2026-07-27 仓库迁移，需分段时间序列 |
| 11 | `OpenHands/software-agent-sdk` | Python | 4,648 | 2026-11-21 | 迁移后的 Agent 后端本体；与 #10 构成“同一血统、跨仓库”的扩散样本 |
| 12 | `SWE-agent/SWE-agent` | Python | 972 | 2026-07-16 | 学术 ACI 奠基项目，研究型代码库 |
| 13 | `SWE-agent/mini-swe-agent` | Python | 760 | 2026-09-03 | 极简 Harness（~100 行核心）；与 #12 构成重型 vs 极简对照 |
| 14 | `browser-use/browser-use` | Python | 4,299 | 2026-11-20 | 浏览器 Agent Harness；检验“禁区”假设是否只在编码域成立 |

### 2.4 Framework / SDK runtime（6）

> 这一组不是终端产品，而是被大量下游 Harness 复用的 Agent 运行时。它们提供了 POHE 面板中最高密度的 canonical exemplar（`openai-agents-python` 命中 12/52 个 Pattern，`mastra` 命中 5 个），是检验“核心机制由谁维护”的关键对照。

| # | Slug | 语言 | PR refs | 最后提交 | 定位与观测重点 |
|---|---|---|---|---|---|
| 15 | `openai/openai-agents-python` | Python | 4,275 | 2026-11-20 | OpenAI 官方 Agents SDK；P01/P02/P03 等核心循环 Pattern 的 canonical 样本 |
| 16 | `mastra-ai/mastra` | TypeScript | 22,735 | 2026-11-20 | 大型 Agent 平台 Monorepo；bot 提交占比高，是研究“平台型仓库的 Agent 归因”样本 |
| 17 | `crewAIInc/crewAI` | Python | 6,174 | 2026-11-20 | 多 Agent 协作框架；角色/任务编排层 |
| 18 | `langchain-ai/langgraph` | Python | 6,373 | 2026-11-20 | 图式编排与 checkpoint/persistence；P13/P26 的典型样本 |
| 19 | `google/adk-python` | Python | 3,720 | 2026-11-20 | Google Agent Development Kit；与 Gemini CLI 同厂不同层，检验组织内部分工 |
| 20 | `huggingface/smolagents` | Python | 2,067 | 2026-11-20 | 极简代码 Agent 库；与 mini-swe-agent 构成“极简”双样本 |

---

## 3. 从 POHE 41 仓库面板到 20 个样本的取舍

POHE 现场指南的 41 仓库面板包含 36 个 repository families。把其中所有被点名的仓库按“是否有足够 PR 历史支撑 RQ1”筛一遍，得到下表。

### 3.1 入选

上述 20 个。除 `Aider-AI/aider`（1,323）、`SWE-agent/SWE-agent`（972）、`mini-swe-agent`（760）外，其余 17 个全历史 PR ref 均超过 2,000，窗口内预计均有数百至数千条 PR。

### 3.2 落选及原因

| 仓库 | 落选原因 |
|---|---|
| `openclaw/openclaw` | 全历史 135,711 个 PR ref、窗口内 13 万+ commit，单一作者占 7 万 commit。量级与提交结构异常（疑似历史重写/大规模生成提交），会主导任何汇总统计。**建议单列案例研究，不进面板。** |
| `mingju-c/HarnessForge` | 窗口内 4 个 commit、0 个 PR ref。无可分析的 PR 历史。 |
| `JIA-Lab-research/CarryOn` | 窗口内 8 个 commit、0 个 PR。 |
| `google-research/rrsi` | 窗口内 4 个 commit、12 个 PR。样本量不足以做仓库内检验。 |
| `google-research/harness2` | 窗口内 21 个 commit、171 个 PR。可作定性附录，不进主面板。 |
| `Darwin-Agent/HarnessX` | 窗口内 29 个 commit、24 个 PR。同上。 |
| `china-qijizhifeng/agentic-harness-engineering` | 窗口内 49 个 commit、11 个 PR。同上。 |
| `affaan-m/ECC` | Agent 配置/技能集合，不是可运行的 Harness 运行时；无核心控制流可分层。 |
| `OpenHands/automation` | 事件驱动的自动化工作流服务，属于 OpenHands 生态的周边组件，与 #10/#11 重叠且核心层不在本仓库。 |
| `microsoft/agent-framework` | 2026-11-21 探测时仓库不可公开访问（0 branch / 0 PR ref），无法纳入可复现样本。 |
| `microsoft/autogen` | 与 crewAI/langgraph 同属编排框架；在 6 个框架名额中，其 POHE canonical 命中数与 PR 量均低于入选者。 |
| `openai/openai-agents-js` | 与 `openai-agents-python` 同源；保留 Python 版以避免同一组织的重复计数。 |
| `agno-agi/agno`、`microsoft/agent-framework` 等其余框架 | 同上：框架层名额已由 canonical 密度更高、PR 历史更长的 6 个占满。 |

### 3.3 研究型 Harness 的处理

`HarnessX`、`HarnessForge`、`harness2`、`rrsi`、`CarryOn`、`agentic-harness-engineering` 这 6 个研究型仓库，PR 数量都在 0–24 之间。它们对“Agent 如何改 Harness”这个问题几乎没有统计信息，但**作为机制样本仍有价值**：它们实现了 POHE 中的 E 家族（harness evolution）机制。处理方式：不进入 20 仓库主面板，在 RQ3 的“范式扩散”部分作为**机制来源**单独列出，不参与比例检验。这样既不牺牲统计功效，也不丢掉“自我改进机制在哪里被发明”的线索。

---

## 4. 治理状态与时间边界

- `RooCodeInc/Roo-Code`：2026-05-15 最后提交，仓库归档。合入率统计以归档日为右边界截断。
- `Aider-AI/aider`：2026-05-22 最后提交，进入低频维护。只做仓库内时间序列，不与高活跃仓库比绝对量。
- `continuedev/continue`：2026-07-20 后无提交。窗口覆盖其 14.6 个月，仍可用；报告中标注“后半段为静默期”。
- `SWE-agent/SWE-agent`：2026-07-16 后无提交；`mini-swe-agent` 活跃至 2026-09。两者构成“重型停更、极简继续”的对照。
- `OpenHands/OpenHands`：2026-07-27 #15397 清空 Python 后端，迁至 `software-agent-sdk`。RQ2/RQ3 时间序列在此断开；#10 与 #11 的 PR 不能简单相加。
- `anomalyco/opencode` 与 `sst/opencode` 同一 `repo.id`，按 id 去重。

---

## 5. 数据量与抽样（更新）

20 仓库的全历史 PR ref 合计约 17.6 万；窗口内估计 8–11 万条。相比 10 仓库方案，普查成本约翻倍，但仍在 REST 限额内：

- **元数据普查**：约 800–1,100 次 REST 请求（100 条/页），约 15 分钟。
- **明细抽样**：6,000 条，按 `repo × tier × quarter` 分层，Tier 1（bot/自主）优先全量；GraphQL 约 2,000–2,500 点/千条，预计 1.5–2 小时。
- **每仓库保底**：150 条。对 `mini-swe-agent`（760 全历史）、`SWE-agent`（972）等小仓库，明细覆盖率会很高（20%–40%），可直接做仓库内比较。

统计功效：若 Tier 1 占 2%，8 万条样本约有 1,600 条；即便按仓库拆分为 20 格，每格仍有约 80 条。Tier 2 通常更大。因此 RQ1 可以做**仓库内三档描述 + Agent/人类二分检验**；分仓库 × 分季度的三档细分会变稀，只做置信区间，不做多重比较。

---

## 6. 已知偏差与处理

| 偏差 | 影响 | 处理 |
|---|---|---|
| 隐性 AI 使用（Cursor/Claude Code 无 trailer） | Tier 3 被污染，Agent 贡献被低估 | Tier 3 定义为“无显性声明的基线组”；结论措辞为“显性可归因的下界” |
| 机器人账号命名不规范 | Tier 1 漏判 | bot 名单 + `author.type == Bot` + 正文模板正则三路召回；抽样复核漏判率 |
| 大厂仓库由内部员工集中提交 | 合入率虚高 | 以仓库内对比为主；跨仓库只比相对差值 |
| 归档/停更仓库 | 合入率结构性下降 | 以归档/停更日为右边界；RQ3 中单独处理 |
| 同源仓库（cline/Roo、gemini-cli/qwen-code、OpenHands/SDK） | 观测不独立 | 统计检验按“仓库族”聚类稳健标准误；描述统计仍按仓库展示 |
| 平台型仓库 bot 提交占比高（mastra） | 归因分布被 bot 主导 | 将平台维护 bot 与代码生成 Agent 分开：前者归 EXCLUDED 或 other_bot，后者才是 Tier 1 |
| 仓库改名/迁移 | 重复计数或时间序列断裂 | 以 `repo.id` 为主键；OpenHands 迁移日断开 |

---

## 7. 交付物流转

- 本清单 → `pipeline/config/repos.yaml`（机器可读，含 category、slug、archived_at、aliases）
- 抓取结果 → `data/evolution2watch.sqlite`
- 分析快照 → `data/derived/*.parquet`
- 图表 → `figures/`
- 最终报告 → `reports/final_report.md`
