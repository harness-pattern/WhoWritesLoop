# Phase 1 / 交付物 B：Harness 架构分层词表（Pointcut Taxonomy v1.0）

> 用途：把每个 PR 的变更文件路径映射到 Harness 的功能分层，使「Agent 改了什么」可跨仓库比较。
> 设计原则：**按功能角色分层，不按目录名分层**。Monorepo 里 `packages/ui` 和 `src/core` 可能在同一层，必须按职责判定。

---

## 1. 分层定义

除原计划的 4 层外，增设两个**非 Harness 层**作为对照组。原因：cline、opencode、OpenHands 等仓库中 50%+ 的变更发生在 UI/文档/官网，如果不单独剥离，会把「Agent 大量修改 UI」误读为「Agent 深入核心」，严重污染 RQ2。

| ID | 层名 | 定义 | 典型内容 |
|---|---|---|---|
| **L1** | **Core Loop / Orchestrator** | 决定 Agent「下一步做什么」的控制流 | 主循环、状态机、任务/子 Agent 调度、规划与反思、重试与回退、终止条件、并发模型 |
| **L2** | **Context & Memory** | 决定 Agent「看到什么、记得什么」 | System prompt 模板、上下文压缩/截断、RAG/代码索引、会话持久化、规则与技能定义、配置加载 |
| **L3** | **Tools & Environment** | 决定 Agent「能做什么、被允许做什么」 | 工具/MCP 接口、Shell/浏览器/文件执行器、diff 应用、权限校验、沙箱隔离、模型 Provider 适配、对外 API/协议 |
| **L4** | **Eval & Infra** | 支撑研发与度量的工程基建 | 测试、benchmark 适配、CI/CD、遥测与 trace、构建脚本、lint/类型配置 |
| **L0** | **Product Surface**（对照） | 面向用户的界面与内容，不改变 Harness 行为 | Webview/UI 组件、TUI 渲染、官网、i18n、示例应用、截图 |
| **LD** | **Docs**（对照） | 纯文档 | README、docs/、changelog、注释性 md |

**为什么把 Docs 单列**：Agent 在文档类 PR 上表现最好、占比最高，如果混进 L2/L4 会系统性高估 Agent 的架构参与度。Docs 是重要的对照，但不是 Pointcut。

**为什么把 Provider 适配放进 L3**：模型 Provider（OpenAI/Anthropic/Gemini 适配器）在架构上等价于「外部能力接口」，与工具适配同属高耦合、低风险的扩展点。这是检验「Agent 只做 Adapter」假设的关键类别。

---

## 2. 判定优先级（Classification Precedence）

同一文件可能匹配多条规则。按以下顺序**首次命中即停**：

1. **测试与基准**：路径含 `/test/`、`/tests/`、`__tests__`、`.test.`、`.spec.`、`_test.py`、`test_*.py`、`/e2e/`、`/evals/`、`/benchmarks?/` → **L4**
2. **CI / 构建 / 工程配置**：`.github/`、`.gitlab-ci`、`Dockerfile`、`docker/`、`Makefile`、`pyproject.toml`、`package.json`、`tsconfig*.json`、`*.lock`、`.eslintrc*`、`biome.json`、`ruff.toml` → **L4**
3. **文档**：`*.md`、`*.mdx`、`docs/`、`website/`、`README*`、`CHANGELOG*`、`LICENSE` → **LD**（例外：`.agents/`、`.claude/`、`.clinerules/`、`.gemini/`、`.roo/` 下的 md 是**运行时规则**；`queries/`、`prompts/` 下的 md 是**提示词模板**——这两类归 L2，不归 LD）
4. **产品界面**：`webview-ui/`、`packages/ui/`、`packages/tui/`、`packages/desktop/`、`packages/session-ui/`、`gui/`、`src/components/`、`src/hooks/`（React）、`services/site/`、`src/i18n/`、`assets/`、`public/` → **L0**
5. **功能层规则**（见第 3 节各仓库映射表）
6. **兜底**：`UNCLASSIFIED`。报告中必须披露未分类文件占比；若 >10%，说明词表覆盖不足，需修订。

> 测试优先于一切：`core/src/core/__tests__/loop.test.ts` 归 L4 而非 L1。但在计算「核心层触及」时，会单独看**非测试文件**是否触及 L1（见 §5）。

---

## 3. 各仓库路径映射表

> 路径为仓库根相对路径，`**` 表示任意深度。表中只列**改变 Harness 行为**的目录；未列出的默认按 §2 优先级落到 L0/LD/L4，或标 UNCLASSIFIED。
> 版本：基于 2026-11-21 各仓库默认分支 HEAD 的目录树；历史 PR 使用旧路径时，由 §4 的路径演化补丁处理。

### 3.1 `openai/codex`（Rust）

| 路径 | 层 | 说明 |
|---|---|---|
| `codex-rs/core/**` | L1 | 主循环、会话、turn 执行 |
| `codex-rs/core-plugins/**` | L3 | 插件机制 |
| `codex-rs/exec-server/**` | L3 | 命令执行服务（沙箱边界） |
| `codex-rs/apply-patch/**` | L3 | diff/patch 应用 |
| `codex-rs/codex-mcp/**`、`codex-rs/rmcp-client/**` | L3 | MCP 客户端与工具协议 |
| `codex-rs/windows-sandbox-rs/**`、`codex-rs/network-proxy/**`、`codex-rs/linux-sandbox/**` | L3 | 沙箱与网络权限 |
| `codex-rs/app-server/**`、`codex-rs/app-server-protocol/**`、`codex-rs/protocol/**` | L3 | 对外协议/接口契约 |
| `codex-rs/state/**`、`codex-rs/thread-store/**`、`codex-rs/config/**` | L2 | 会话状态与配置 |
| `codex-rs/skills/**`、`codex-rs/hooks/**` | L2 | 技能与钩子（上下文注入） |
| `codex-rs/tui/**` | L0 | 终端 UI |
| `codex-rs/cli/**`、`sdk/**` | L0 | 入口与 SDK 封装（面向用户） |
| `codex-rs/utils/**`、`codex-rs/login/**`、`codex-rs/codex-api/**` | L3 | 支撑设施/认证/API 客户端 |
| `codex-rs/ext/**` | L3 | 扩展 |

### 3.2 `google-gemini/gemini-cli`（TypeScript）

| 路径 | 层 | 说明 |
|---|---|---|
| `packages/core/src/core/**` | L1 | GeminiClient 主循环 |
| `packages/core/src/agents/**`、`scheduler/**` | L1 | 子 Agent 与调度 |
| `packages/core/src/context/**`、`prompts/**` | L2 | 上下文管理与提示词 |
| `packages/core/src/tools/**`、`mcp/**`、`sandbox/**` | L3 | 工具/MCP/沙箱 |
| `packages/core/src/policy/**`、`safety/**` | L3 | 权限与安全边界 |
| `packages/core/src/config/**`、`services/**` | L2 | 配置与服务层 |
| `packages/core/src/telemetry/**` | L4 | 遥测 |
| `packages/cli/**` | L0 | CLI 交互层 |
| `packages/sdk/**`、`a2a-server/**` | L3 | SDK 与 Agent-to-Agent 接口 |
| `packages/vscode-ide-companion/**` | L0 | IDE 伴生 UI |
| `.gemini/**` | L2 | 仓库自身的 Gemini 规则/技能（dogfooding 证据） |
| `tools/caretaker-agent/**`、`tools/gemini-cli-bot/**` | L4 | 仓库自动化机器人（GitHub 工作流） |

### 3.3 `anomalyco/opencode`（TypeScript / Go）

| 路径 | 层 | 说明 |
|---|---|---|
| `packages/core/src/session/**`、`machine/**` | L1 | 会话循环与状态机 |
| `packages/core/src/tool/**`、`plugin/**`、`mcp/**`、`codemode/**` | L3 | 工具、插件、MCP |
| `packages/core/src/database/**`、`config/**` | L2 | 持久化与配置 |
| `packages/ai/**` | L3 | 模型 Provider 适配 |
| `packages/server/**`、`protocol/**`、`schema/**`、`client/**` | L3 | 服务端与协议 |
| `packages/cli/**`、`tui/**`、`ui/**`、`app/**`、`desktop/**`、`session-ui/**` | L0 | 用户界面 |
| `services/site/**` | L0 | 官网 |
| `packages/util/**`、`data/**` | L2 | 工具库/数据层 |

### 3.4 `Aider-AI/aider`（Python）

| 路径 | 层 | 说明 |
|---|---|---|
| `aider/coders/**` | L1 | Architect/Editor 双模型管线 |
| `aider/main.py`、`aider/commands.py` | L1 / L0 | 主循环 / 命令解析 |
| `aider/queries/**` | L2 | 提示词模板 |
| `aider/repomap.py` | L2 | 代码索引 |
| `aider/models.py`、`aider/llm.py` | L3 | 模型适配 |
| `aider/io.py`、`aider/args.py` | L0 | 交互与参数 |
| `aider/website/**` | LD | 官网即文档 |
| `tests/**` | L4 | 测试 |

### 3.5 `cline/cline`（TypeScript Monorepo）

| 路径 | 层 | 说明 |
|---|---|---|
| `apps/vscode/src/core/**` | L1 | Task 循环、Plan/Act |
| `sdk/packages/core/src/**`（`task/`、`agent/`、`state/`） | L1 | 新 SDK 运行时 |
| `apps/vscode/src/services/**` | L3 | MCP、浏览器、终端等服务 |
| `sdk/packages/llms/**` | L3 | Provider 适配 |
| `apps/vscode/src/shared/**`、`packages/types` 类 | L1 | 跨层契约（改动即接口变更） |
| `sdk/packages/core/src/context/**`、`prompts/**` | L2 | 上下文与提示词 |
| `webview-ui/**`、`apps/cline-hub/**`、`apps/examples/**` | L0 | UI 与示例 |
| `evals/**` | L4 | 评测 |
| `.clinerules/**`、`.claude/**`、`.agents/**` | L2 | 仓库自身规则/技能 |

### 3.6 `continuedev/continue`（TypeScript / Python）

| 路径 | 层 | 说明 |
|---|---|---|
| `core/edit/**`、`diff/**`、`nextEdit/**` | L1 | 编辑应用与下一步预测的核心逻辑 |
| `core/autocomplete/**` | L0 | 产品功能（补全） |
| `core/tools/**` | L3 | 工具 |
| `core/llm/**`、`packages/openai-adapters/**` | L3 | 模型适配 |
| `core/context/**`、`indexing/**`、`promptFiles/**` | L2 | 上下文/索引/提示词 |
| `core/config/**`、`packages/config-yaml/**` | L2 | 配置 |
| `extensions/vscode/**`、`intellij/**`、`gui/**`、`extensions/cli/**` | L0 | IDE/CLI 界面 |
| `core/protocol/**` | L3 | 协议 |

### 3.7 `RooCodeInc/Roo-Code`（TypeScript）

| 路径 | 层 | 说明 |
|---|---|---|
| `src/core/**` | L1 | Task 循环、模式（Mode）调度 |
| `src/services/**` | L3 | MCP、浏览器、代码索引等服务 |
| `src/api/**` | L3 | Provider 适配 |
| `webview-ui/**`、`apps/cli/**`、`apps/docs/**` | L0 / LD | UI、CLI、文档站 |
| `packages/types/**`、`src/shared/**` | L1 | 契约 |
| `.roo/**` | L2 | 仓库自身规则 |

### 3.8 `OpenHands/OpenHands`（Python → TypeScript，**仓库发生过拆分**）

**关键事实**：截至 2026-11-21 的 HEAD，该仓库是一个 Electron + React 桌面应用，Python Agent 后端已迁出。窗口早段的 PR 修改的是 Python `openhands/**`，晚段修改的是 `src/**` 前端。**必须按时间分段解释，否则会把「仓库职责变更」误判为「Agent 从核心撤退」**。

| 路径 | 层 | 时期 |
|---|---|---|
| `openhands/controller/**`、`openhands/agenthub/**` | L1 | 2025 全年（历史） |
| `openhands/memory/**`、`openhands/core/prompts/**` | L2 | 历史 |
| `openhands/runtime/**`、`openhands/tools/**`、`openhands/security/**` | L3 | 历史 |
| `openhands/server/**`、`openhands/events/**` | L3 | 历史 |
| `frontend/**`、`src/**`、`electron/**` | L0 | 当前 |
| `tests/**`、`__tests__/**` | L4 | 全期 |

### 3.9 `SWE-agent/SWE-agent`（Python）

| 路径 | 层 | 说明 |
|---|---|---|
| `sweagent/agent/**` | L1 | Agent 主循环 |
| `sweagent/run/**` | L1 | 运行编排 |
| `sweagent/tools/**`、`environment/**` | L3 | ACI 工具与环境 |
| `tools/**`（`windowed`、`search`、`registry`、`web_browser`） | L3 | 具体工具实现 |
| `config/**` | L2 | 配置与提示词 |
| `sweagent/inspector/**` | L4 | 轨迹观测 |
| `trajectories/**` | L4 | 轨迹数据 |

### 3.10 `SWE-agent/mini-swe-agent`（Python）

| 路径 | 层 | 说明 |
|---|---|---|
| `src/minisweagent/agents/**` | L1 | 极简主循环 |
| `src/minisweagent/run/**` | L1 | 运行入口 |
| `src/minisweagent/environments/**`、`tools/**`、`models/**` | L3 | 环境、工具、模型 |
| `src/minisweagent/config/**` | L2 | 配置 |
| `tests/**` | L4 | 测试 |


### 3.11 `QwenLM/qwen-code`（TypeScript，gemini-cli 分叉）

| 路径 | 层 | 说明 |
|---|---|---|
| `packages/core/src/(core|agents|scheduler)/**` | L1 | 主循环、子 Agent、调度 |
| `packages/core/src/(context|prompts|config|services)/**` | L2 | 上下文、提示词、配置 |
| `packages/core/src/(tools|mcp|sandbox|policy|safety)/**` | L3 | 工具、MCP、沙箱、权限 |
| `packages/core/src/telemetry/**` | L4 | 遥测 |
| `packages/(cli|web-shell|vscode-ide-companion|qwen-live|live-host)/**` | L0 | 终端/Web/IDE 界面 |
| `packages/(sdk-*|acp-bridge|managed-agent-server|cua-driver|channels)/**` | L3 | SDK 与协议接口 |
| `docs/design/**` | LD | 设计文档 |

### 3.12 `aaif-goose/goose`（Rust 核心 + TypeScript UI）

| 路径 | 层 | 说明 |
|---|---|---|
| `crates/goose/src/agents/**` | L1 | Agent 主循环与扩展 |
| `crates/goose/src/(session|config|prompts|recipe|skills)/**` | L2 | 会话、配置、提示词、配方 |
| `crates/goose/src/(providers|mcp|security|plugins|slash_commands|acp)/**` | L3 | Provider、MCP、权限、插件 |
| `crates/goose-cli/**`、`ui/**` | L0 | CLI 与桌面 UI |
| `documentation/**` | LD | 文档站 |

### 3.13 `OpenHands/software-agent-sdk`（Python）

| 路径 | 层 | 说明 |
|---|---|---|
| `openhands-sdk/openhands/sdk/(agent|conversation|automation|subagent|launch)/**` | L1 | 会话循环、子 Agent、启动编排 |
| `openhands-sdk/openhands/sdk/(context|condenser|workspace|settings|skills|prompts)/**` | L2 | 上下文压缩、工作区、配置、技能 |
| `openhands-sdk/openhands/sdk/(tool|llm|mcp|security|secret|git|hooks|io|event|extensions)/**` | L3 | 工具、模型、MCP、安全、事件 |
| `openhands-sdk/openhands/sdk/(observability|testing|logger|utils)/**` | L4 | 观测与测试设施 |
| `openhands-tools/**`、`openhands-agent-server/**`、`clients/**` | L3 | 工具集、Agent Server、客户端 |
| `examples/**` | LD | 示例 |

### 3.14 `browser-use/browser-use`（Python）

| 路径 | 层 | 说明 |
|---|---|---|
| `browser_use/agent/**`（`loop.py`、`service.py`、`judge.py`） | L1 | 浏览器 Agent 主循环与判定 |
| `browser_use/(browser|tools|mcp)/**` | L3 | 浏览器控制、工具、MCP |
| `browser_use/skills/**` | L2 | 可复用任务流程（技能） |
| `browser_use/repl/**` | L3 | 交互式执行环境 |
| `browser_use/telemetry/**` | L4 | 遥测 |
| `tests/**`、`skills/**`（仓库根，QA 脚本） | L4 | 测试与评测 |

### 3.15 `openai/openai-agents-python`（Python）

| 路径 | 层 | 说明 |
|---|---|---|
| `src/agents/run_internal/**`、`realtime/**`、`voice/**`、`handoffs/**` | L1 | 运行循环、实时会话、交接 |
| `src/agents/memory/**` | L2 | 会话记忆 |
| `src/agents/(sandbox|models|mcp|extensions)/**`、`tool_guardrails.py`、`tool_context.py` | L3 | 沙箱、模型适配、MCP、工具护栏 |
| `src/agents/tracing/**`、`util/**`、`testing/**` | L4 | 追踪与测试 |
| `src/agents/(agent|run|result|stream_events).py` | L1 | 核心运行时对象 |
| `examples/**`、`docs/**` | LD | 示例与文档 |

### 3.16 `mastra-ai/mastra`（TypeScript Monorepo）

| 路径 | 层 | 说明 |
|---|---|---|
| `packages/core/src/(agent|agent-controller|loop|workflows)/**` | L1 | Agent 循环、控制器、工作流 |
| `packages/core/src/(storage|workspace|processors|knowledge|stream)/**`、`packages/memory/**`、`packages/rag/**` | L2 | 存储、记忆、上下文处理、RAG |
| `packages/core/src/(tools|llm)/**`、`packages/(server|mcp*|client-sdks|deployers|auth)/**` | L3 | 工具、模型、服务端与协议 |
| `packages/(evals|datasets)/**`、`packages/core/src/(evals|datasets)/**` | L4 | 评测与数据集 |
| `packages/(playground|playground-ui|cli)/**`、`mastracode/(tui|factory-ui)/**` | L0 | 控制台、CLI、TUI |
| `docs/**`、`templates/**` | LD | 文档与模板 |

### 3.17 `crewAIInc/crewAI`（Python）

| 路径 | 层 | 说明 |
|---|---|---|
| `lib/crewai/src/crewai/(agents|flow|crew|task|process)/**` | L1 | Agent、任务、流程编排 |
| `lib/crewai/src/crewai/(memory|knowledge|rag)/**` | L2 | 记忆、知识库、RAG |
| `lib/crewai/src/crewai/(tools|llms|mcp|a2a)/**` | L3 | 工具、模型、MCP、A2A |
| `lib/crewai/src/crewai/(telemetry|utilities)/**` | L4 | 遥测与工具函数 |
| `lib/crewai/src/crewai/cli/**` | L0 | CLI |
| `docs/**` | LD | 文档（含大量版本快照） |

### 3.18 `langchain-ai/langgraph`（Python）

| 路径 | 层 | 说明 |
|---|---|---|
| `libs/langgraph/langgraph/(pregel|graph|channels|func)/**`、`runtime.py` | L1 | 图执行引擎、通道、运行时 |
| `libs/checkpoint*/**`、`libs/langgraph/langgraph/store/**` | L2 | 检查点、持久化状态 |
| `libs/(cli|sdk-py)/**` | L0 / L3 | CLI（L0）、SDK（L3） |
| `libs/prebuilt/**` | L1 | 预置 Agent |
| `examples/**` | LD | 示例 |

### 3.19 `google/adk-python`（Python）

| 路径 | 层 | 说明 |
|---|---|---|
| `src/google/adk/(flows|agents|workflow|runners)/**` | L1 | 执行流、Agent、运行器 |
| `src/google/adk/(sessions|memory|artifacts)/**` | L2 | 会话、记忆、产物 |
| `src/google/adk/(tools|models|mcp|auth|plugins|integrations|a2a)/**` | L3 | 工具、模型、MCP、鉴权、集成 |
| `src/google/adk/(evaluation|telemetry)/**` | L4 | 评测与遥测 |
| `src/google/adk/(cli|web)/**` | L0 | CLI 与 Web UI |

### 3.20 `huggingface/smolagents`（Python）

| 路径 | 层 | 说明 |
|---|---|---|
| `src/smolagents/agents.py` | L1 | 极简 Agent 主循环 |
| `src/smolagents/(memory|serialization).py` | L2 | 记忆与序列化 |
| `src/smolagents/(models|tools|default_tools|local_python_executor|remote_executors|mcp_client|tool_validation).py` | L3 | 模型、工具、执行器、MCP |
| `src/smolagents/(monitoring|utils).py` | L4 | 监控与工具函数 |
| `src/smolagents/(gradio_ui|cli|vision_web_browser).py` | L0 | UI 与交互入口 |


---

## 4. 路径演化补丁（Path Evolution Patches）

仓库在 18 个月内会重命名目录。若不处理，历史 PR 会大量落到 UNCLASSIFIED。做法：维护 `pipeline/config/path_aliases.yaml`，把旧路径前缀映射到新前缀，**按 PR 创建时间选择生效的映射**。

已知需要处理的：

| 仓库 | 旧路径 | 新路径 | 生效期 |
|---|---|---|---|
| opencode | `packages/opencode/src/**` | `packages/core/src/**` | 2025 年内迁移 |
| cline | `src/core/**`（单包时期） | `apps/vscode/src/core/**` | Monorepo 化之后 |
| continue | `core/**` 的 `llm/` 子目录重组 | 以实际抓取到的路径为准 | 动态维护 |
| OpenHands | `openhands/**`（Python） | 迁出至独立包 | 2026 年 |
| codex | `codex-rs/**` 子 crate 拆分 | 动态维护 | 全期 |

实现方式：抓取完成后，统计 UNCLASSIFIED 路径的 top-N，人工确认后补进 aliases，再重跑映射。**这是一次性校准，不是每轮都做**。

---

## 5. 衍生指标

### 5.1 跨层耦合度（Cross-layer Coupling）

对每个 PR 的非测试、非文档文件计算：

- `layers_touched` = 命中的不同 Harness 层集合（L1–L4）的大小，取值 0–4
- `touches_core` = 是否触及 L1（布尔）
- `core_share` = L1 文件增删行数 / 全部增删行数
- `cross_layer` = `layers_touched ≥ 2`

「大 PR 噪声」的处理：`layers_touched` 作为连续变量进入模型，而不是把跨层 PR 强行归入单层。同时报告 `layers_touched ≥ 3` 的 PR 作为「结构性大改」的敏感度分析子集。

### 5.2 变更性质（Change Type）

规则引擎初判，LLM 复核：

| 标签 | 判定条件（满足任一） |
|---|---|
| `structural` | ① 触及 L1 且删除行数/新增行数 > 0.3；② 重命名或删除文件数 ≥ 3；③ 触及 ≥ 2 个 Harness 层且变更文件 ≥ 10；④ 标题/正文命中 `refactor|restructure|rewrite|migrate|redesign|decouple|extract` |
| `additive` | 新增文件占比 > 60%，且删除行数 < 新增行数的 10%，且未触及 L1 |
| `fix` | 标题命中 `fix|bug|crash|regression|hotfix` 且未触发 structural |
| `docs` | 仅 LD 层文件 |
| `test_only` | 仅 L4 层文件且全为测试 |
| `ui` | 仅 L0 层文件 |

`structural` 与 `additive` 互斥，优先判 structural。

### 5.3 架构熵增代理指标（Entropy Proxy）

无法对全量 PR 做 AST 分析，因此用三个可计算的代理：

1. **文件扩散度**：`changed_files / max(1, net_loc/100)` —— 同样改动量下触及更多文件，倾向散弹式修改
2. **删除比**：`deletions / (additions + deletions)` —— 抽象提取通常伴随删除旧实现；硬编码堆叠则删除比低
3. **接口文件命中**：是否修改 `interface_files`（每仓库维护的核心契约文件清单，如 `core/src/core/types.ts`、`sweagent/agent/agents.py`）

LLM 深标注子样本上，额外标注「抽象提取 vs 条件分支堆叠」作为金标准，用于验证代理指标的方向性（报告 Spearman 相关，不宣称因果）。

---

## 6. 词表覆盖率的验收

Phase 1 验收标准：**20 个仓库的默认分支目录树 100% 可映射**（不允许有顶层目录无法归类）。抓取后追加验收：**PR 变更文件按行数加权，UNCLASSIFIED ≤ 5%**。超过则修订本词表并重跑，修订记录写入 `docs/taxonomy_changelog.md`。
