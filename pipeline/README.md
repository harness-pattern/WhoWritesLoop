# evolution2watch 数据管线

## 0. 前置：GitHub token

在项目根目录新建文件（任选其一，内容为一行 PAT，不要加引号）：

```
github_token.txt
.github_token
```

或设置环境变量 `GITHUB_TOKEN`。Token 需要 `public_repo` 权限（只读公开仓库即可）。

## 1. 抓取

```bash
cd <project>
python3 pipeline/fetch.py repos      # 解析 repo_id、归档状态
python3 pipeline/fetch.py list       # 窗口内 PR 元数据全量（census）
python3 pipeline/fetch.py sample --total 6000 --per-repo-min 150
python3 pipeline/fetch.py details    # 抽样 PR 的 files/commits/reviews（GraphQL）
python3 pipeline/fetch.py status
```

`list` 是断点安全的：重复执行只会 upsert。`details` 只处理 `detail_status=0` 的 PR。
抓取量大时，分批执行 `details`（每次 10 分钟上限），直到 `status` 中 pending=0。

## 2. 打标

```bash
python3 pipeline/rules.py            # Tier + 架构层 + 变更类型
```

覆盖率检查：脚本末尾打印 UNCLASSIFIED 占比。>5% 时按 `docs/02_taxonomy.md` §4 补路径别名。

## 3. LLM-as-a-Judge

```bash
python3 pipeline/judge.py fetch-patches --n 300
python3 pipeline/judge.py export --n 300 --size 40
# 用 docs/03_labeling_spec.md §2.3 的 schema 标注 data/judge/batch_*.jsonl
python3 pipeline/judge.py ingest --file data/judge/labels_01.jsonl
python3 pipeline/judge.py kappa --truth data/calibration/adjudicated.csv --pred judge
python3 pipeline/judge.py kappa --truth data/calibration/adjudicated.csv --pred rule
```

## 4. 分析

```bash
python3 pipeline/analyze.py
```

输出：

- `reports/tables/*.csv`：RQ1/RQ2/RQ3 的统计表
- `reports/summary.json`：报告生成用的关键数字
- `figures/fig1..fig6.png`

## 5. 数据库

`data/evolution2watch.sqlite`，表结构见 `pipeline/db.py`。常用查询：

```sql
-- Tier 分布
SELECT tier, COUNT(*) FROM prs WHERE detail_status!=3 GROUP BY tier;
-- 某仓库某层的 PR
SELECT number, title FROM prs WHERE repo_id=1 AND layers LIKE '%"L1"%';
```

## 6. 口径提醒

- 合入率分母排除 cutoff 后仍未决的 PR（`analyze.py` 已处理）。
- Tier 3 = 无显性声明，不等于纯人类。
- RQ2 的层分布基于明细抽样，已按 repo×tier 加权；报告需同时给未加权仓库内数字。
- OpenHands 在 2026-07-27 发生仓库迁移，时间序列必须断开。
