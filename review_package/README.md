# Human Review Package — Repository Mining Audit

This package lets independent reviewers verify the mining, attribution, and layering behind the paper *Who Rewrites the Loop?* It is **not** a request to re-run the study. It is a targeted audit of the parts where automation can be wrong: PR identity, agent attribution, architecture layer, change type, repository counts, revert links, and pattern hits.

The paper reports 135,331 retained PRs, 7,205 detail records, and a 120-record model-assisted adjudication. That adjudication was performed by a model, not by humans. This package exists to replace or supplement it with human judgment.

---

## 1. Files

| File | Purpose |
|---|---|
| `review.html` | Self-contained review app. Opens in any browser; no server, no network calls except the GitHub links you click. Exports `review_form_filled.csv`. |
| `review_sample.csv` | The 120 sampled PRs with rule labels and GitHub URLs. Do not edit. |
| `review_form.csv` | Blank CSV form, one row per sampled PR. Use this if you prefer a spreadsheet to the HTML app. |
| `codebook.md` | Definitions, precedence rules, and edge cases. Read this first. |
| `INSTRUCTIONS.md` | Full reviewer protocol (English): six decisions, hard-case matrix, two-reviewer and adjudication rules, common mistakes. |
| `INSTRUCTIONS.zh.md` | 中文评审手册，与英文版逐节对应。 |
| `EXAMPLES.md` | Ten worked records (English), including five deliberate rule errors. |
| `EXAMPLES.zh.md` | 10 条完整中文示例，含 5 条故意保留的规则错误。 |
| `repo_counts.csv` | Expected PR count per repository plus a GitHub search URL. Fill `observed_prs` after checking. |
| `revert_sample.csv` | 15 revert PRs. Verify the claimed target exists and is the PR that was actually reverted. |
| `pattern_sample.csv` | 16 PRs that matched RQ3 pattern keywords. Judge whether the pattern is substantively present. |
| `compute_agreement.py` | Reads a filled form and writes `agreement_report.md` with accuracy, Cohen's κ, error breakdown, and count deviations. |
| `manifest.json` | Seed, sample size, tier counts, and SHA-256 of every generated file. |
| `generate.py` | Reproduces the package from the database with seed 20261121. |
| `fetch_patches.py` | Downloads the 120 `.diff` excerpts into `../data/review_patches/`; run once before `generate.py`. |

**Annotator mode is the default.** A reviewer does not need to read the paper: every question carries its definition, examples, and negative cases inline. The automated labels are hidden until **show automated labels (audit mode)** is enabled; export always derives the rule-vs-annotator agreement columns.

The app has a **中文 / EN** toggle in the header: it switches the interface, question labels, warning, and the short codebook without reloading. The full codebook and the example index remain English; the Chinese versions of both handbook and examples are embedded as separate markdown files.

**Self-contained mode.** `review.html` embeds all 120 records, each PR's metadata, file list with assigned layers and status, commit subjects, body excerpt, a 7 KB diff excerpt, the rule's evidence string, the full codebook, and a browser-side Cohen's κ calculator. Answers autosave in the browser, so a reviewer can refresh safely; **Export CSV** writes the form. A reviewer only needs this one file plus the GitHub links they choose to open. The CSV files exist for spreadsheet workflows and for the formal agreement script.

---

## 2. Sampling design

- 120 PRs drawn from the 7,205-PR detail sample.
- **20 PRs per architecture layer** (L1, L2, L3, L4, L0, LD), so the layer audit is not dominated by the L4-heavy population.
- Inside each layer, **7 Tier 1, 7 Tier 2, 6 Tier 3**; tier totals are 42/42/36.
- Within each layer--tier cell, PRs are drawn round-robin across the 20 repositories after shuffling, so a single large repository cannot dominate.
- PRs whose diff is entirely generated or lock files are excluded; they are covered by the GEN layer in the full data.
- Seed: `20261121`. The manifest records the hashes.
- The sample intentionally includes known hard cases (bot accounts that look human, docs-only PRs labeled T1, compatibility fixes labeled structural). These are not bugs in the sample; they are the cases the audit must adjudicate.

---

## 3. Reviewer protocol

Budget about **2–3 minutes per PR**, so 4–6 hours for the 120 records. Split into three sessions if needed. Do not rush the identity check; a wrong URL invalidates the row.

### Step 0 — Prepare

1. Open `review.html` in a browser. Metadata, file list, commits, body, diff excerpt, rule evidence, and the codebook are embedded; `codebook.md` is the same text outside the app.
2. Answers autosave in `localStorage`; you can refresh, close the tab, and resume. Use **Export CSV** when done.
3. Enter your reviewer name at export time. Use one form per reviewer.
4. When all records are complete, click **Agreement** to see browser-side κ before exporting.

### Step 1 — Identity (every record)

Open the GitHub link. Confirm:

- the PR number and title match the row;
- the merge status matches (`merged`, `closed-unmerged`, `open`);
- the author matches.

If any of these fail, mark the identity field `N` and note what you saw. A mismatch is a mining defect, not a labeling dispute.

### Step 2 — Tier

Apply the codebook decision tree. Mark `agree` or `disagree` and, if disagreeing, select the correct tier. Pay special attention to:

- bot accounts whose login does not end in `[bot]`;
- human-looking accounts that are GitHub Apps;
- T2 rows whose only evidence is a commit trailer (open the commits tab);
- T3 rows that mention AI in prose but carry no artifact.

### Step 3 — Primary layer

Use the precedence order: tests → generated → docs → product surface → CI → functional layer. Then choose the layer with the largest line weight. Record the layer you believe is primary, not every layer the PR touches.

### Step 4 — Change type

Use the decision tree in the codebook. Structural is reserved for contract/interface/concurrency/security changes or cross-layer rewrites; a compatibility fix is a fix even if the diff is large.

### Step 5 — Confidence and notes

Record 1–5 and a short note for every disagreement. Cite the file or hunk.

### Step 6 — Repository-level counts (one pass, ~30 minutes)

Open `repo_counts.csv`. For each repository, open the GitHub search URL and read the PR count. Enter it in `observed_prs`. A deviation above 1% means the census has a pagination or filtering defect; note whether the GitHub search includes bots or excludes them.

### Step 7 — Revert links (~20 minutes)

Open `revert_sample.csv`. For each row, confirm on GitHub that the PR is a revert, that the claimed target exists, and that the target is the PR that was actually reverted. Mark `target_found` and `reviewer_verdict` (`confirmed`, `wrong-target`, `not-a-revert`).

### Step 8 — Pattern hits (~20 minutes)

Open `pattern_sample.csv`. For each row, judge whether the PR substantively introduces or changes the named pattern, or merely mentions it. Mark `is_substantive` (`yes`/`no`) and cite the evidence.

---

## 4. Producing the agreement report

If you used the HTML app, it downloads `review_form_filled.csv`. If you used the CSV template, fill it in place.

```bash
python3 compute_agreement.py \
  --form review_form_filled.csv \
  --sample review_sample.csv \
  --counts repo_counts.csv
```

The script writes `agreement_report.md` and `agreement_summary.json`.

If two reviewers each produce a form, run the script twice. To compare reviewers with each other, put reviewer 1's final labels in the `*_corrected` columns of a copy of reviewer 2's form and compare the `*_rule` columns; or open an issue and we will add an inter-reviewer mode.

---

## 5. Acceptance thresholds

| Check | Threshold | What to do if it fails |
|---|---|---|
| Title / merge-status identity | 100% | Fix the mining pipeline before using the record. |
| Tier κ | ≥ 0.80 | Inspect the confusion table; revise bot/trailer rules or the codebook. |
| Primary-layer κ | ≥ 0.65 | The L1/L2 boundary is the usual culprit; add interface-file rules or tighten the precedence. |
| Change-type κ | ≥ 0.60 | Usually structural-vs-fix; tighten the structural definition. |
| Repository count deviation | ≤ 1% per repo | Check pagination, date filtering, and bot exclusions. |
| Revert target accuracy | ≥ 90% | Fix the revert-link parser. |
| Pattern-hit precision | Report only | Do not tune the RQ3 curves on the same rows. |

Do **not** tune the rule on the same 120 records and then report the tuned κ as independent. If a dimension fails, revise, draw a fresh sample with a new seed, and audit again.

---

## 6. Roles and independence

- **Reviewer A and Reviewer B** label independently. Neither sees the other's form.
- **Adjudicator** resolves disagreements after both forms are submitted, using the codebook and the GitHub diff. Record the adjudicated label in a third file.
- The rule author does not label. The rule author may answer questions about the codebook but must not suggest labels for individual records.

---

## 7. What this package does and does not establish

It establishes whether the mining pipeline and the rule engine agree with human judgment on a stratified sample. It does **not** establish that the layer taxonomy is the only useful one, that the pattern keywords capture implementation, or that the 120 records are representative of all 135,331 PRs. Those are design choices, reported as such in the paper's threats-to-validity section.

## 8. Data handling

The sample contains only public GitHub metadata and URLs. No private data, tokens, or reviewer identities are embedded. The HTML app makes no network requests; it only opens GitHub links when you click them.
