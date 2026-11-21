# Who Rewrites the Loop?

**Human versus Agent Authorship in the Recursive Self-Improvement of Open-Source Agent Harnesses**

Haoyi Xiong, Yekun Chai

This repository contains the paper, the mining pipeline, the analysis, and the human-review package for an empirical study of 20 open-source agent harnesses (135,331 retained pull requests, May 2025 -- November 2026).

## Website

The project site is `index.html`, designed for GitHub Pages at <https://harness-pattern.github.io/WhoWritesLoop/>. It links the paper, the figures, the datasets, and the self-contained review app.

## Paper

- [`paper/main.pdf`](paper/main.pdf) — ACM `sigconf` two-column PDF, 10 pages
- [`paper/main.tex`](paper/main.tex) — LaTeX source (line numbers enabled for review)
- [`paper/make_figures.py`](paper/make_figures.py) — regenerates the three English PDF vector figures

Build:

```bash
cd paper
latexmk -pdf main.tex
```

The ACM class is vendored as `paper/acmart.cls` because the base TeX Live image does not ship it.

## Key findings

- Explicitly agent-attributable PRs are **5.2%** of decided PRs (Tier 1 2.87%, Tier 2 2.33%). This is a lower bound on actual AI involvement.
- Agent PRs merge less often overall (Mantel--Haenszel OR **0.709**, 95% CI 0.682--0.738), but the effect ranges from **+15 pp** to **-43 pp** across repositories; governance, not agent brand, explains the split.
- Autonomous agents are concentrated in tests, infrastructure, UI, and documentation: **13.2%** touch the core loop, versus **26.0%** of unmarked PRs, and **15.8%** are structural changes, versus **22.9%**.
- Co-authored PRs are the exception: **28.8%** touch the core and **30.2%** are structural, making human--agent pairing the main channel for architectural change.

## Repository layout

| Path | Contents |
|---|---|
| `paper/` | ACM paper source, PDF, vector figures, figure generator |
| `pipeline/` | GitHub crawling, tier attribution, layer mapping, analysis |
| `docs/` | Sample-pool rationale, pointcut taxonomy, labeling specification |
| `reports/` | Final report (Chinese), `summary.json`, 15 statistical tables |
| `figures/` | Report figures (PNG) |
| `review_package/` | Self-contained human-review app, codebook, agreement script |
| `data/derived/` | Cleaned census (135,331 PRs) and detail sample (7,205 PRs), CSV gzip |
| `data/judge/` | Model-assisted adjudication batches and labels |
| `data/patches/` | PR patch excerpts used for adjudication |

## Data availability

The cleaned datasets are included:

- `data/derived/prs_census.csv.gz` — 135,331 PRs, metadata and rule labels
- `data/derived/prs_detail.csv.gz` — 7,205 PRs with layer/change-type labels
- `data/judge/labels_01..03.jsonl` — 120 adjudicated records

The full 506 MB SQLite database (`data/evolution2watch_data.sqlite`) is **not** committed because it exceeds GitHub's file-size limit. It can be rebuilt with the pipeline, or reconstructed from the CSV exports for most analyses.

## Reproduce

```bash
export E2W_DB=/tmp/evolution2watch.sqlite   # the mounted project folder does not support SQLite write locks
python3 pipeline/fetch.py repos
python3 pipeline/fastlist.py --workers 4
python3 pipeline/fetch.py sample --total 6000 --per-repo-min 150
python3 pipeline/fetch.py details
python3 pipeline/rules.py
python3 pipeline/analyze.py
```

Set `GITHUB_TOKEN` or put a token in `github_token.txt` (ignored by git). The window, repository list, bot exclusions, and agent account map live in `pipeline/config/repos.yaml`.

## Human review

`review_package/review.html` is self-contained: it embeds 120 stratified PRs (20 per architecture layer, 7/7/6 Tier 1/2/3 inside each layer), each PR's file list, commit subjects, body excerpt, the full codebook, and a browser-side Cohen's kappa calculator. A reviewer can work with this single file and export `review_form_filled.csv`; the formal agreement report is produced by `review_package/compute_agreement.py`.

See [`review_package/README.md`](review_package/README.md) for the protocol and acceptance thresholds.

## Important caveats

- Tier 3 is an **unmarked baseline**, not a pure-human control; unmarked AI assistance contaminates it.
- Tier 2 is undercounted in the census because commit trailers are only visible in the 7,205-PR detail sample.
- The 120-record adjudication was performed by a model, not by human double-coding; the paper reports rule--adjudication kappa (0.566 change type, 0.579 core touch) and treats the layer results as subject to 10--20 pp classification uncertainty.
- RQ3 pattern detection is lexical and left-censored; the curves measure change intensity, not confirmed adoption.
- OpenHands migrated its Python backend to `software-agent-sdk` on 2026-07-27; the time series is broken at that point. Cline/Roo-Code, Gemini CLI/Qwen Code, and OpenHands/SDK are same-lineage pairs and are not independent.

## References

The paper cites the Google harness line directly:

- Object-Oriented Harness (OO-Harness), arXiv:2610.28380
- Harness^2: Recursive Agent Harnessing for an Open World, arXiv:2610.14224
