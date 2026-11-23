# Codex AI-assisted review — 2026-11-23

This submission contains all 120 PR annotations from `review_package/review.html`,
with reviewer identity `Codex (AI-assisted review)`. Each row includes title and
merge-status checks, tier, primary layer, change type, confidence, and a rationale
citing the relevant files or authorship evidence.

This is a single model-assisted review. It does not satisfy the two-independent-human-reviewer
protocol and is not an adjudicated human gold standard. Codebook examples and the
embedded source data were visible during preparation; no strict blinded-review
claim is made.

## Files

- `review_form_filled.csv`: the page's 17-column export schema; 120 unique rows
  ordered S001–S120. Line endings are normalized to LF for Git; parsed values are unchanged. Review date uses Asia/Shanghai (2026-11-23), whereas the
  page's native export used the preceding UTC date at the time of review.
- `evidence_manifest.json`: sample/form SHA-256 hashes and each public PR's URL,
  head SHA, fetch timestamp, file count, commit count, and available API patch count.

## Evidence and limitations

Title and merge status were checked against live GitHub REST metadata for every
record. Complete paginated file lists and commit messages were retrieved for all
120 PRs. The original page truncates 13 file lists to 20 files and lacks cached
diffs for S046, S049, S057, and S096; live API evidence supplemented those excerpts.
Patch excerpts and relevant additional hunks were inspected for classification;
retrieving a complete inventory does not mean every line of every large PR was read.
Raw API responses remain in the local review archive; this submission includes
only the compact public-source index.

Labels describe the available PR diffs, including unexpectedly broad or mixed
changes. Notes flag ambiguous taxonomy/attribution decisions and scope anomalies,
such as the release-automation PR S018 and the 691-file addition in S049. S001's
current author is `ghost`, despite the historical author shown in the package;
its title and merge-status checks still match.

All 120 title and merge-status checks match. Confidence counts: 3 records at 2,
41 at 3, 38 at 4, and 38 at 5 (mean 3.925/5). Repository-level counts, revert links,
and pattern-hit forms were outside this 120-record task and remain unreviewed.

## Validation

Checked sample identity/order, unique IDs, allowed field values, complete notes,
comparison-column consistency, and CSV round-trip. Browser export labels and notes
match the submitted CSV; only the documented UTC versus local date differs.
The repository's unmodified `compute_agreement.py` ran against this submission
in a temporary directory so its fixed-location summary output did not replace
existing repository results.

Rule-versus-AI agreement (descriptive, not human-validation evidence):

| Dimension | n | Agreement | Cohen's κ |
|---|---:|---:|---:|
| Tier | 120 | 89.2% | 0.836 |
| Primary layer | 120 | 59.2% | 0.510 |
| Change type | 120 | 60.8% | 0.487 |

Disagreements are retained for maintainer review; they are not assertions that
every differing rule label is wrong. No study conclusions or rule labels are
updated by this submission.
