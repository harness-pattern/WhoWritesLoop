#!/usr/bin/env python3
"""Generate English-label figures for the paper from analysis tables."""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAB = ROOT / "reports" / "tables"
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# ---------------------------------------------------------------- forest plot
t = pd.read_csv(TAB / "rq1_within_repo_tests.csv").sort_values("diff_pp")
fig, ax = plt.subplots(figsize=(6.4, 5.2))
y = np.arange(len(t))
colors = ["#2b6cb0" if v >= 0 else "#c53030" for v in t["diff_pp"]]
ax.scatter(t["diff_pp"], y, c=colors, s=34, zorder=3)
ax.axvline(0, color="#718096", lw=0.8, ls="--")
ax.set_yticks(y)
ax.set_yticklabels(t["repo"], fontsize=8)
for i, (_, r) in enumerate(t.iterrows()):
    ax.annotate(f"{r['diff_pp']:+.1f}", (r["diff_pp"], i), xytext=(6, -3),
                textcoords="offset points", fontsize=7, color="#2d3748")
ax.set_xlabel("Merge-rate difference: agent PRs minus unmarked PRs (percentage points)")
ax.set_title("Within-repository merge-rate gap")
ax.margins(x=0.18)
fig.tight_layout()
fig.savefig(OUT / "fig_merge_diff_en.pdf")
fig.savefig(OUT / "fig_merge_diff_en.png", dpi=220)
plt.close(fig)

# ---------------------------------------------------------------- layer heatmap
h = pd.read_csv(TAB / "rq2_heatmap_repo_layer.csv")
h["group"] = h["group"].replace({"Agent (显性)": "Agent (T1+T2)", "Human (无声明)": "Unmarked (T3)"})
h["layer"] = h["layer"].map({"L1": "L1 core", "L2": "L2 context", "L3": "L3 tools", "L4": "L4 infra"})
piv = h.pivot_table(index="repo", columns=["group", "layer"], values="touch_rate")
piv = piv.reindex(columns=[
    ("Agent (T1+T2)", "L1 core"), ("Agent (T1+T2)", "L2 context"),
    ("Agent (T1+T2)", "L3 tools"), ("Agent (T1+T2)", "L4 infra"),
    ("Unmarked (T3)", "L1 core"), ("Unmarked (T3)", "L2 context"),
    ("Unmarked (T3)", "L3 tools"), ("Unmarked (T3)", "L4 infra"),
])
piv.columns = [f"{g}\n{l}" for g, l in piv.columns]
fig, ax = plt.subplots(figsize=(8.2, 6.8))
sns.heatmap(piv, cmap="YlOrRd", vmin=0, vmax=1, annot=True, fmt=".2f",
            annot_kws={"size": 7}, cbar_kws={"label": "Share of PRs touching layer"},
            linewidths=0.4, linecolor="white", ax=ax)
ax.set_xlabel("")
ax.set_ylabel("")
ax.set_title("Layer touch rate by repository and attribution group")
plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=7)
plt.setp(ax.get_yticklabels(), fontsize=7)
fig.tight_layout()
fig.savefig(OUT / "fig_layer_heatmap_en.pdf")
fig.savefig(OUT / "fig_layer_heatmap_en.png", dpi=220)
plt.close(fig)

# ---------------------------------------------------------------- diffusion lines
q = pd.read_csv(TAB / "rq3_pattern_quarterly.csv")
name_map = {
    "MCP 协议接入": "MCP integration",
    "上下文压缩": "Context compaction",
    "Sub-agent 并行": "Sub-agent parallelism",
    "Diff/Patch 应用": "Diff/patch application",
    "Checkpoint/回滚": "Checkpoint/rollback",
    "Skills/Rules 机制": "Skills/rules",
}
q["pattern"] = q["pattern"].map(name_map)
piv = q.pivot(index="quarter", columns="pattern", values="share") * 100
order = ["Skills/rules", "MCP integration", "Context compaction",
         "Checkpoint/rollback", "Sub-agent parallelism", "Diff/patch application"]
piv = piv[order]
fig, ax = plt.subplots(figsize=(7.0, 4.0))
markers = ["o", "s", "^", "D", "v", "P"]
for i, col in enumerate(piv.columns):
    ax.plot(piv.index, piv[col], marker=markers[i], ms=4, lw=1.6, label=col)
ax.set_ylabel("Share of PRs mentioning pattern (%)")
ax.set_xlabel("")
ax.set_title("In-window intensity of harness patterns")
ax.legend(frameon=False, fontsize=7.5, ncol=2, loc="upper left")
ax.set_ylim(bottom=0)
ax.tick_params(axis="x", labelsize=8)
fig.tight_layout()
fig.savefig(OUT / "fig_diffusion_en.pdf")
fig.savefig(OUT / "fig_diffusion_en.png", dpi=220)
plt.close(fig)

print("wrote", sorted(p.name for p in OUT.glob("*_en.png")))
