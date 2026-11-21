#!/usr/bin/env python3
"""Analysis for RQ1/RQ2/RQ3. Reads SQLite, writes tables + figures.

Usage:
  python3 pipeline/analyze.py            # all
  python3 pipeline/analyze.py --rq1      # subset
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP", "Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TAB = ROOT / "reports" / "tables"
FIG = ROOT / "figures"
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

TIER_LABEL = {"T1": "T1 自主 Agent", "T2": "T2 协作/辅助", "T3": "T3 无显性声明"}
COLORS = {"T1": "#d62728", "T2": "#ff7f0e", "T3": "#4c72b0"}
LAYERS = ["L1", "L2", "L3", "L4", "L0", "LD", "UNCLASSIFIED"]
LAYER_LABEL = {
    "L1": "L1 Core Loop", "L2": "L2 Context/Memory", "L3": "L3 Tools/Sandbox",
    "L4": "L4 Eval/Infra", "L0": "L0 Product UI", "LD": "LD Docs", "UNCLASSIFIED": "未分类",
}


def load(con) -> pd.DataFrame:
    q = """
    SELECT p.*, r.slug, r.category,
           (SELECT COUNT(*) FROM pr_files f WHERE f.repo_id=p.repo_id AND f.number=p.number) AS n_files
    FROM prs p JOIN repos r USING(repo_id)
    WHERE p.detail_status != 3
    """
    df = pd.read_sql_query(q, con)
    for c in ["created_at", "closed_at", "merged_at"]:
        df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
    df["tier"] = df["tier"].fillna("UNKNOWN")
    df["merged"] = df["merged_at"].notna()
    df["decided"] = df["merged"] | ((df["state"].str.lower() == "closed") & df["closed_at"].notna())
    df["quarter"] = df["created_at"].dt.to_period("Q").astype(str)
    df["agent_group"] = np.where(df["tier"].isin(["T1", "T2"]), "Agent (显性)", "Human (无声明)")
    df["ttm_hours"] = (df["merged_at"] - df["created_at"]).dt.total_seconds() / 3600
    df["review_rounds"] = df["review_comments"].fillna(0)
    return df


def primary_layer(s):
    if not isinstance(s, str) or not s:
        return "UNKNOWN"
    d = json.loads(s)
    return max(d, key=d.get) if d else "UNKNOWN"


# ------------------------------------------------------------------ RQ1
def rq1(df: pd.DataFrame, cutoff: pd.Timestamp) -> dict:
    print("\n=== RQ1 ===")
    d = df[(df["created_at"] <= cutoff) & df["decided"]].copy()
    det = d[d["detail_status"] == 1].copy()
    rows = []
    for (repo, tier), g in d.groupby(["slug", "tier"]):
        merged = int(g["merged"].sum())
        n = len(g)
        rows.append({
            "repo": repo, "tier": tier, "n": n, "merged": merged,
            "merge_rate": merged / n if n else np.nan,
            "median_ttm_hours": g.loc[g["merged"], "ttm_hours"].median(),
        })
    t = pd.DataFrame(rows).sort_values(["repo", "tier"])
    t.to_csv(TAB / "rq1_by_repo_tier.csv", index=False)

    # within-repo: agent (T1+T2) vs human
    tests = []
    for repo, g in d.groupby("slug"):
        a = g[g["tier"].isin(["T1", "T2"])]
        h = g[g["tier"] == "T3"]
        if len(a) < 20 or len(h) < 20:
            continue
        tab = [[int(a["merged"].sum()), int((~a["merged"]).sum())],
               [int(h["merged"].sum()), int((~h["merged"]).sum())]]
        or_, p = stats.fisher_exact(tab)
        ar = a["merged"].mean()
        hr = h["merged"].mean()
        tests.append({
            "repo": repo, "n_agent": len(a), "n_human": len(h),
            "merge_rate_agent": ar, "merge_rate_human": hr,
            "diff_pp": (ar - hr) * 100, "odds_ratio": or_, "p_value": p,
        })
    tt = pd.DataFrame(tests)
    if len(tt):
        tt["p_adj_bh"] = tt["p_value"].rank(method="first") / len(tt) * tt["p_value"]  # placeholder
        tt["p_adj_bh"] = _bh(tt["p_value"].values)
        tt.to_csv(TAB / "rq1_within_repo_tests.csv", index=False)

    # pooled Mantel-Haenszel across repos (agent vs human)
    mh = None
    strata = []
    for repo, g in d.groupby("slug"):
        a = g[g["tier"].isin(["T1", "T2"])]
        h = g[g["tier"] == "T3"]
        if len(a) < 5 or len(h) < 5:
            continue
        strata.append([[int(a["merged"].sum()), int((~a["merged"]).sum())],
                       [int(h["merged"].sum()), int((~h["merged"]).sum())]])
    if len(strata) >= 2:
        mh = mantel_haenszel(strata)

    # agent family
    fam = (det[det["tier"].isin(["T1", "T2"])]
           .groupby(["agent_family", "tier"])
           .agg(n=("number", "size"), merged=("merged", "sum"),
                median_review=("review_rounds", "median"))
           .reset_index())
    fam["merge_rate"] = fam["merged"] / fam["n"]
    fam.sort_values("n", ascending=False).to_csv(TAB / "rq1_agent_family.csv", index=False)

    # rework: Mann-Whitney within repo, agent vs human (review rounds)
    rw = []
    for repo, g in d.groupby("slug"):
        a = g[g["tier"].isin(["T1", "T2"])]["review_rounds"].dropna()
        h = g[g["tier"] == "T3"]["review_rounds"].dropna()
        if len(a) >= 10 and len(h) >= 10:
            u, p = stats.mannwhitneyu(a, h, alternative="two-sided")
            rw.append({"repo": repo, "median_agent": a.median(), "median_human": h.median(),
                       "p_value": p, "n_agent": len(a), "n_human": len(h)})
    pd.DataFrame(rw).to_csv(TAB / "rq1_rework_mannwhitney.csv", index=False)

    # reverts
    rev = detect_reverts(df)
    rev.to_csv(TAB / "rq1_revert_rates.csv", index=False)

    # figure: composition
    comp = (df[df["tier"].isin(["T1", "T2", "T3"])]
            .groupby(["slug", "tier"]).size().unstack(fill_value=0))
    comp = comp.div(comp.sum(axis=1), axis=0)
    sort_col = "T1" if "T1" in comp.columns else comp.columns[0]
    comp = comp.sort_values(sort_col)
    ax = comp.plot(kind="barh", stacked=True, figsize=(9, 5.5),
                   color=[COLORS.get(c) for c in comp.columns])
    ax.set_xlabel("PR 占比"); ax.set_ylabel("")
    ax.legend(title="", loc="lower right", frameon=False)
    ax.set_title("各仓库 PR 的归因构成")
    plt.tight_layout(); plt.savefig(FIG / "fig1_tier_composition.png", dpi=180); plt.close()

    # figure: merge rate forest
    if len(tt):
        tt2 = tt.sort_values("diff_pp")
        y = np.arange(len(tt2))
        fig, ax = plt.subplots(figsize=(7, 0.45 * len(tt2) + 1.5))
        ax.scatter(tt2["diff_pp"], y, color="#d62728", zorder=3)
        ax.axvline(0, color="grey", lw=0.8, ls="--")
        ax.set_yticks(y); ax.set_yticklabels(tt2["repo"])
        for i, (_, r) in enumerate(tt2.iterrows()):
            ax.annotate(f"{r['diff_pp']:+.1f}pp", (r["diff_pp"], i), textcoords="offset points",
                        xytext=(6, -3), fontsize=8)
        ax.set_xlabel("合入率差值：显性 Agent PR − 无声明 PR（百分点）")
        ax.set_title("仓库内合入率差值（负值=Agent 更难合入）")
        plt.tight_layout(); plt.savefig(FIG / "fig2_merge_rate_diff.png", dpi=180); plt.close()

    return {"n_analyzed": len(d), "mh": mh,
            "overall_merge_rate": float(d["merged"].mean()),
            "agent_share": float(d["tier"].isin(["T1", "T2"]).mean()),
            "tier_counts": d["tier"].value_counts().to_dict()}


def _bh(p):
    p = np.asarray(p, dtype=float)
    order = np.argsort(p)
    n = len(p)
    adj = np.empty(n)
    prev = 1.0
    for rank, idx in enumerate(order[::-1], start=1):
        val = min(prev, p[idx] * n / (n - rank + 1))
        adj[idx] = val
        prev = val
    return adj


def mantel_haenszel(strata):
    """Pooled odds ratio across 2x2 strata ([[a,b],[c,d]] per stratum)."""
    num = den = 0.0
    e_sum = v_sum = 0.0
    for t in strata:
        (a, b), (c, d) = t
        n = a + b + c + d
        if n < 2:
            continue
        num += a * d / n
        den += b * c / n
        e_sum += (a + b) * (a + c) / n
        v_sum += (a + b) * (c + d) * (a + c) * (b + d) / (n * n * (n - 1))
    if den == 0 or num == 0:
        return {"or": None, "ci_low": None, "ci_high": None, "p": None}
    or_ = num / den
    var = 0.0
    for t in strata:
        (a, b), (c, d) = t
        n = a + b + c + d
        if n < 2:
            continue
        var += (a * d * (b + c) + b * c * (a + d)) / (2 * n * n)
    se = np.sqrt(var / (num * den))
    a_tot = sum(t[0][0] for t in strata)
    chi2 = (a_tot - e_sum) ** 2 / v_sum if v_sum else np.nan
    p = 1 - stats.chi2.cdf(chi2, 1) if v_sum else np.nan
    return {"or": float(or_), "ci_low": float(np.exp(np.log(or_) - 1.96 * se)),
            "ci_high": float(np.exp(np.log(or_) + 1.96 * se)), "p": float(p)}


def detect_reverts(df: pd.DataFrame) -> pd.DataFrame:
    rev = df[df["title"].fillna("").str.match(r'(?i)^revert\b')].copy()
    if rev.empty:
        return pd.DataFrame(columns=["tier", "merged", "reverted", "revert_rate"])
    merged = df[df["merged"]].copy()
    sha_to_pr = {r["merge_commit_sha"]: (r["repo_id"], r["number"])
                 for _, r in merged.iterrows() if r["merge_commit_sha"]}
    targets = []
    for _, r in rev.iterrows():
        tgt = None
        m = re.search(r"This reverts commit ([0-9a-f]{7,40})", r["body"] or "", re.I)
        if m:
            pref = m.group(1)
            for sha, key in sha_to_pr.items():
                if sha.startswith(pref):
                    tgt = key
                    break
        if not tgt:
            m = re.search(r"(?i)reverts?\s+#(\d+)", (r["body"] or "") + " " + (r["title"] or ""))
            if m:
                tgt = (r["repo_id"], int(m.group(1)))
        if tgt:
            targets.append(tgt)
    tgt_df = pd.DataFrame(targets, columns=["repo_id", "number"]).drop_duplicates()
    merged["reverted"] = merged.apply(
        lambda r: ((r["repo_id"], r["number"]) in set(map(tuple, tgt_df.values))), axis=1
    )
    out = (merged.groupby("tier").agg(n_merged=("number", "size"), reverted=("reverted", "sum"))
           .reset_index())
    out["revert_rate"] = out["reverted"] / out["n_merged"]
    return out


# ------------------------------------------------------------------ RQ2
def rq2(df: pd.DataFrame) -> dict:
    print("\n=== RQ2 ===")
    d = df[df["detail_status"] == 1].copy()
    if d.empty:
        return {}
    d["primary_layer"] = d["layers"].apply(primary_layer)

    # sampling weights: population per repo/tier / sample per repo/tier
    pop = df.groupby(["repo_id", "tier"]).size().rename("pop")
    smp = d.groupby(["repo_id", "tier"]).size().rename("smp")
    w = pd.concat([pop, smp], axis=1).dropna()
    w["w"] = w["pop"] / w["smp"]
    d = d.merge(w[["w"]], left_on=["repo_id", "tier"], right_index=True, how="left")
    d["w"] = d["w"].fillna(1.0)

    # layer distribution among harness-touching PRs, by tier (weighted)
    rows = []
    for tier in ["T1", "T2", "T3"]:
        g = d[d["tier"] == tier]
        if g.empty:
            continue
        for layer in LAYERS[:-1]:
            rows.append({"tier": tier, "layer": layer,
                         "pr_share": g["primary_layer"].eq(layer).mean(),
                         "touch_rate": g["layers"].apply(
                             lambda s: layer in (json.loads(s) if s else {})).mean(),
                         "n": len(g)})
    lt = pd.DataFrame(rows)
    lt.to_csv(TAB / "rq2_layer_by_tier.csv", index=False)

    # repo x layer x agent
    hrows = []
    for (repo, grp), g in d.groupby(["slug", "agent_group"]):
        for layer in ["L1", "L2", "L3", "L4"]:
            hrows.append({"repo": repo, "group": grp, "layer": layer,
                          "touch_rate": g["layers"].apply(
                              lambda s: layer in (json.loads(s) if s else {})).mean(),
                          "n": len(g)})
    hm = pd.DataFrame(hrows)
    hm.to_csv(TAB / "rq2_heatmap_repo_layer.csv", index=False)

    # core touch rate + logistic with repo FE
    d["touches_core"] = d["touches_core"].fillna(0).astype(int)
    core = (d.groupby(["slug", "tier"])
            .agg(n=("number", "size"), core_touch=("touches_core", "mean"),
                 mean_layers=("layers_touched", "mean"),
                 structural=("change_type", lambda s: (s == "structural").mean()))
            .reset_index())
    core.to_csv(TAB / "rq2_core_touch_by_repo_tier.csv", index=False)

    # change type distribution
    ct = (d.groupby(["tier", "change_type"]).size().unstack(fill_value=0))
    ct = ct.div(ct.sum(axis=1), axis=0)
    ct.to_csv(TAB / "rq2_change_type_by_tier.csv")

    # statistical tests
    tests = []
    a = d[d["tier"].isin(["T1", "T2"])]; h = d[d["tier"] == "T3"]
    if len(a) and len(h):
        harness_only = d[d["primary_layer"].isin(["L1", "L2", "L3", "L4"])]
        tab = pd.crosstab(harness_only["agent_group"], harness_only["primary_layer"])
        if tab.shape[0] == 2 and tab.shape[1] > 1:
            chi2, p, dof, _ = stats.chi2_contingency(tab)
            tests.append({"test": "layer_distribution_agent_vs_human", "chi2": chi2,
                          "dof": dof, "p_value": p, "cramers_v": np.sqrt(chi2 / (len(harness_only) * (min(tab.shape) - 1)))})
        tab2 = [[int(a["touches_core"].sum()), int((1 - a["touches_core"]).sum())],
                [int(h["touches_core"].sum()), int((1 - h["touches_core"]).sum())]]
        or_, p = stats.fisher_exact(tab2)
        tests.append({"test": "core_touch_agent_vs_human", "odds_ratio": or_, "p_value": p})
    pd.DataFrame(tests).to_csv(TAB / "rq2_tests.csv", index=False)

    # figures
    piv = hm.pivot_table(index="repo", columns=["group", "layer"], values="touch_rate")
    order = [c for c in piv.columns if c[0] == "Agent (显性)"] + [c for c in piv.columns if c[0] != "Agent (显性)"]
    piv = piv[order]
    plt.figure(figsize=(10, 0.45 * len(piv) + 2))
    sns.heatmap(piv, cmap="YlOrRd", vmin=0, vmax=1, annot=True, fmt=".2f",
                cbar_kws={"label": "触及该层的 PR 比例"}, annot_kws={"size": 7})
    plt.title("仓库 × 架构层触及率：显性 Agent vs 无声明")
    plt.xticks(rotation=35, ha="right", fontsize=8)
    plt.tight_layout(); plt.savefig(FIG / "fig3_layer_heatmap.png", dpi=180); plt.close()

    # core touch over time
    d["quarter"] = d["created_at"].dt.to_period("Q").astype(str)
    ts = d.groupby(["quarter", "agent_group"])["touches_core"].mean().unstack()
    if len(ts):
        ax = ts.plot(marker="o", figsize=(8, 4.2), color=["#d62728", "#4c72b0"][:len(ts.columns)])
        ax.set_ylabel("触及 L1 的 PR 比例"); ax.set_xlabel("")
        ax.set_title("核心控制流触及率的时间趋势（明细样本）")
        ax.legend(frameon=False)
        plt.tight_layout(); plt.savefig(FIG / "fig4_core_touch_trend.png", dpi=180); plt.close()
    # weighted tier-level rates (corrects T1 oversampling by repo x tier)
    wrows = []
    for tier, g in d.groupby("tier"):
        wrows.append({
            "tier": tier, "n": len(g),
            "core_touch": float(np.average(g["touches_core"], weights=g["w"])),
            "structural": float(np.average(g["change_type"].eq("structural"), weights=g["w"])),
            "merge_rate": float(np.average(g["merged"], weights=g["w"])),
        })
    wdf = pd.DataFrame(wrows)
    wdf.to_csv(TAB / "rq2_weighted_tier_rates.csv", index=False)
    wa = d[d["tier"].isin(["T1", "T2"])]; wh = d[d["tier"] == "T3"]
    def wor(x):
        a1 = float((x[x["tier"].isin(["T1", "T2"])]["touches_core"] * x[x["tier"].isin(["T1", "T2"])]["w"]).sum())
        return a1
    a1 = float((wa["touches_core"] * wa["w"]).sum()); a0 = float(((1 - wa["touches_core"]) * wa["w"]).sum())
    h1 = float((wh["touches_core"] * wh["w"]).sum()); h0 = float(((1 - wh["touches_core"]) * wh["w"]).sum())
    weighted = {"tiers": wdf.to_dict("records"),
                "agent_core": a1 / (a1 + a0) if (a1 + a0) else None,
                "human_core": h1 / (h1 + h0) if (h1 + h0) else None,
                "core_or": (a1 * h0) / (a0 * h1) if a0 * h1 else None}
    return {"n_detail": len(d), "tests": tests,
            "core_touch_rate": {"agent": float(a["touches_core"].mean()) if len(a) else None,
                                "human": float(h["touches_core"].mean()) if len(h) else None},
            "weighted": weighted}


# ------------------------------------------------------------------ RQ3
PATTERNS = {
    "MCP 协议接入": r"\bMCP\b|model context protocol",
    "上下文压缩": r"compact(ion)?|compress(ion)?\b.*context|context.*(compact|compress|truncat)|summariz.*(context|history)",
    "Sub-agent 并行": r"sub-?agents?|parallel (agent|tool)|multi-?agent",
    "Diff/Patch 应用": r"apply[_ -]?patch|patch apply|apply.*diff|diff apply|str_replace|edit format",
    "Checkpoint/回滚": r"checkpoint|restore.*(state|workspace)|snapshot.*(state|workspace)",
    "Skills/Rules 机制": r"\bskills?\b|AGENTS\.md|CLAUDE\.md|custom instructions|rules? file",
}


def rq3(df: pd.DataFrame) -> dict:
    print("\n=== RQ3 ===")
    merged = df[df["merged"]].copy()
    merged["text"] = (merged["title"].fillna("") + "\n" + merged["body"].fillna("")).str.lower()
    rows = []
    for name, pat in PATTERNS.items():
        rx = re.compile(pat, re.I)
        hit = merged[merged["text"].str.contains(rx, regex=True, na=False)]
        for repo, g in hit.groupby("slug"):
            fm = g["merged_at"].min()
            rows.append({"pattern": name, "repo": repo,
                         "first_merged": fm.date().isoformat(),
                         "left_censored": int(fm <= pd.Timestamp("2025-05-31", tz="UTC")),
                         "n_prs": len(g)})
    diff = pd.DataFrame(rows)
    diff.to_csv(TAB / "rq3_pattern_first_merge.csv", index=False)

    # pattern x tier: who carries each pattern
    prow = []
    for name, pat in PATTERNS.items():
        rx = re.compile(pat, re.I)
        hit = merged[merged["text"].str.contains(rx, regex=True, na=False)]
        if hit.empty:
            continue
        vc = hit["tier"].value_counts()
        prow.append({"pattern": name, "n_prs": len(hit),
                     "T1": int(vc.get("T1", 0)), "T2": int(vc.get("T2", 0)),
                     "T3": int(vc.get("T3", 0)),
                     "agent_share": float(hit["tier"].isin(["T1", "T2"]).mean())})
    pd.DataFrame(prow).to_csv(TAB / "rq3_pattern_tier.csv", index=False)

    # quarterly intensity (share of all merged PRs mentioning the pattern)
    merged["quarter"] = merged["created_at"].dt.to_period("Q").astype(str)
    tot_q = merged.groupby("quarter").size()
    trow = []
    for name, pat in PATTERNS.items():
        rx = re.compile(pat, re.I)
        hit = merged[merged["text"].str.contains(rx, regex=True, na=False)]
        q = hit.groupby("quarter").size().reindex(tot_q.index, fill_value=0)
        for quarter, n in q.items():
            trow.append({"pattern": name, "quarter": quarter,
                         "n": int(n), "share": float(n / tot_q[quarter])})
    pd.DataFrame(trow).to_csv(TAB / "rq3_pattern_quarterly.csv", index=False)

    if len(diff):
        piv = diff.pivot(index="repo", columns="pattern", values="first_merged")
        fig, ax = plt.subplots(figsize=(10, 5))
        dates = pd.to_datetime(piv.stack(), errors="coerce").unstack()
        base = dates.min().min()
        days = dates.apply(lambda c: (c - base).dt.days)
        sns.heatmap(days, annot=dates.apply(lambda c: c.dt.strftime("%Y-%m")),
                    fmt="", cmap="Blues", cbar_kws={"label": "距最早出现的天数"}, ax=ax,
                    annot_kws={"size": 7})
        ax.set_title("标志性 Harness Pattern 的窗口内首次命中时间（2025-05 = 窗口前已存在）")
        plt.xticks(rotation=35, ha="right")
        plt.tight_layout(); plt.savefig(FIG / "fig5_pattern_diffusion.png", dpi=180); plt.close()

    # clustering on repo x tier behavior vectors
    d = df[df["detail_status"] == 1].copy()
    feats = []
    for (repo, tier), g in d.groupby(["slug", "tier"]):
        if len(g) < 20:
            continue
        layers = {l: g["layers"].apply(lambda s: l in (json.loads(s) if s else {})).mean()
                  for l in ["L1", "L2", "L3", "L4", "L0", "LD"]}
        feats.append({"repo": repo, "tier": tier, "n": len(g),
                      **{f"share_{k}": v for k, v in layers.items()},
                      "core_share": g["core_share"].mean(),
                      "layers_touched": g["layers_touched"].mean(),
                      "structural": (g["change_type"] == "structural").mean(),
                      "median_files": g["changed_files"].median()})
    fd = pd.DataFrame(feats)
    if len(fd) >= 4:
        X = fd.drop(columns=["repo", "tier", "n"]).fillna(0)
        Z = (X - X.mean()) / X.std(ddof=0).replace(0, 1)
        from scipy.cluster.hierarchy import linkage, dendrogram
        from sklearn.cluster import KMeans
        k = min(4, max(2, len(fd) // 6))
        km = KMeans(n_clusters=k, n_init=20, random_state=42).fit(Z)
        fd["cluster"] = km.labels_
        fd.to_csv(TAB / "rq3_behavior_clusters.csv", index=False)
        fig, ax = plt.subplots(figsize=(8, 4.5))
        sns.scatterplot(data=fd, x="share_L1", y="share_L3", hue="cluster", style="tier",
                        s=90, ax=ax, palette="tab10")
        for _, r in fd.iterrows():
            ax.annotate(r["repo"].split("/")[-1], (r["share_L1"], r["share_L3"]),
                        fontsize=6, xytext=(3, 3), textcoords="offset points")
        ax.set_xlabel("L1 触及率"); ax.set_ylabel("L3 触及率")
        ax.set_title("Repo × Tier 行为聚类（k=%d）" % k)
        plt.tight_layout(); plt.savefig(FIG / "fig6_behavior_clusters.png", dpi=180); plt.close()
    return {"patterns": len(PATTERNS), "repos_with_pattern": int(diff["repo"].nunique()) if len(diff) else 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", default="2026-09-21")
    args = ap.parse_args()
    con = db.connect()
    df = load(con)
    print(f"loaded {len(df)} PRs; detail={int((df['detail_status']==1).sum())}")
    if df.empty:
        print("no data yet")
        return
    cutoff = pd.Timestamp(args.cutoff, tz="UTC")
    out = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "n_prs": len(df),
        "n_detail": int((df["detail_status"] == 1).sum()),
        "rq1": rq1(df, cutoff),
        "rq2": rq2(df),
        "rq3": rq3(df),
    }
    with open(ROOT / "reports" / "summary.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print("\nwrote reports/summary.json and tables/figures")


if __name__ == "__main__":
    main()
