# Review Output Schema

The review produces two files: `<skill-name>-review.json` (machine-readable)
and `<skill-name>-review.md` (human-readable). The JSON is the source of
truth; the markdown is generated from it.

```json
{
  "skill_name": "example-skill",
  "reviewed_at": "2026-09-08T00:00:00Z",
  "overall_verdict": "pass | pass_with_suggestions | needs_work | blocked",
  "category_scores": {
    "compliance": "pass | blocker",
    "structure_and_progressive_disclosure": "pass | minor | major | blocker",
    "description_and_triggering": "pass | minor | major | blocker",
    "writing_style_and_content": "pass | minor | major | blocker",
    "safety": "pass | blocker"
  },
  "metrics": {
    "skill_md_body_line_count": 482,
    "description_word_count": 49,
    "resource_file_count": 11,
    "resource_dir_file_counts": {"scripts": 2, "references": 3, "assets": 0},
    "imperative_marker_counts": {"MUST": 0, "NEVER": 1, "ALWAYS": 2},
    "preferred_structure_sections": {"present": ["Purpose", "Workflow"], "missing": ["When NOT to Use"]},
    "declared_tools": ["Bash", "Read"],
    "tools_declared_but_unreferenced": [],
    "tools_referenced_but_undeclared": [],
    "hardcoded_secret_candidates": [],
    "dangerous_shell_pattern_candidates": [],
    "prompt_injection_phrase_candidates": [],
    "prohibited_action_phrase_candidates": [],
    "undeclared_external_hosts": [],
    "security_scan": {"skipped": false, "forced": false, "checks_skipped": [], "reason": null}
  },
  "findings": [
    {
      "id": "F1",
      "category": "description_and_triggering",
      "severity": "major",
      "location": "frontmatter.description",
      "issue": "Description states what the skill does but gives no triggering context — no 'when to use' cues.",
      "current_text": "Formats Excel spreadsheets and cleans up data.",
      "suggested_rewrite": "Formats and cleans up Excel spreadsheets — fixing headers, removing blank rows, standardizing date/number formats. Use this whenever the user mentions a spreadsheet, workbook, .xlsx/.xls/.csv file, or wants tabular data cleaned, reformatted, or fixed, even if they don't say 'Excel' explicitly.",
      "why_it_matters": "The description is the only signal Claude sees before deciding to consult the skill; without an explicit when-clause it will under-trigger."
    }
  ],
  "orphaned_resource_files_confirmed": [],
  "summary": "One-paragraph plain-language summary of overall health and the highest-priority fix."
}
```

**Field notes:**
- `overall_verdict`: `blocked` if any category is `blocker`; `needs_work` if
  any category is `major`; `pass_with_suggestions` if only `minor` findings
  exist; `pass` if everything is clean.
- `findings[].severity`: `minor | major | blocker` (matches rubric.md scale;
  "pass" findings aren't listed individually).
- `findings[].suggested_rewrite`: required for every finding except pure
  structural/compliance facts where the fix is mechanical (e.g. "move file
  X to references/") — for those, `suggested_rewrite` can describe the
  mechanical fix instead of prose.
- `orphaned_resource_files_confirmed`: the subset of the script's raw
  orphan-file candidates that you verified are actually unreferenced,
  after checking for indirect references (e.g. `python -m scripts.foo`).
- `compliance_errors` can include hardcoded-secret findings
  (`metrics.hardcoded_secret_candidates`) — these are hard blockers, always
  reported with the matched value redacted, never in the clear.
- The `*_candidates` metrics fields (dangerous shell patterns, prompt
  injection phrasing, prohibited-action phrasing, undeclared external hosts,
  tool declaration mismatches) are raw regex matches, not verdicts — confirm
  each against real context (per `rubric.md`) before it becomes a finding.
- `metrics.security_scan`: whether the dangerous-shell-pattern,
  prompt-injection, and undeclared-host scans ran. `skipped: true` means the
  skill declared/referenced no shell-executing or network-capable tool, so
  those three `*_candidates` fields are empty lists by default rather than
  confirmed-clean — check this before treating an empty list as "scanned,
  found nothing." `forced: true` means `--force-security-scan` overrode the
  skip. Hardcoded-secret and prohibited-action-phrase scanning are never
  gated by this and always run.

## Self-consistency: the reconciled-review shape

When SKILL.md's Workflow step 6 runs (N independent qualitative passes,
reconciled with `scripts/reconcile_reviews.py`), the reconciler's raw JSON
output has a different shape from the single-run schema above — it's an
intermediate aggregate, not itself a `<skill-name>-review.json`:

```json
{
  "skill_name": "example-skill",
  "runs": 3,
  "threshold": 2,
  "overall_verdict": "needs_work",
  "overall_verdict_by_run": ["blocked", "needs_work", "needs_work"],
  "category_scores": {"compliance": "pass", "safety": "pass", "...": "..."},
  "category_scores_by_run": [{"...": "..."}, {"...": "..."}, {"...": "..."}],
  "findings": [
    {
      "category": "safety",
      "location": "SKILL.md:80",
      "agreement_count": 1,
      "agreement_fraction": 0.3333,
      "confirmed": false,
      "consensus_severity": "blocker",
      "severities_by_run": ["blocker", null, null],
      "representative_issue": "...",
      "representative_suggested_rewrite": "...",
      "representative_why_it_matters": "...",
      "variant_issue_texts": []
    }
  ],
  "confirmed_findings_count": 3,
  "unconfirmed_findings_count": 2,
  "summary": "..."
}
```

**Field notes:**
- `threshold`: minimum `agreement_count` for `confirmed: true` — defaults to
  a simple majority (`floor(runs/2) + 1`), overridable with `--threshold`.
- `overall_verdict`/`category_scores`: recomputed from the *reconciled*
  category scores using the same derivation rule as a single run (see
  above) — not copied from any individual run. Per-category consensus is a
  majority vote across `category_scores_by_run`, ties broken toward the
  more severe value (e.g. a 1-1 split between `pass` and `blocker` resolves
  to `blocker`).
- `findings[]` are grouped by `(category, location)` across all runs, not
  by finding id — free-text `issue` wording can differ run to run even when
  the same underlying problem was caught, so `location` (a file:line or a
  frontmatter field) is the more stable match key. A finding with no
  `location` can't be reliably matched across runs and is kept as its own
  unconfirmed singleton rather than guessed at.
- `representative_issue`/`representative_suggested_rewrite`/
  `representative_why_it_matters`: taken from whichever run's finding at
  that `(category, location)` has a severity matching `consensus_severity`
  (first such run, in input order) — not synthesized. `variant_issue_texts`
  lists the differently-worded `issue` text from any other run that matched
  the same location, for reference.
- This reconciled JSON is **not** what gets written to
  `<skill-name>-review.json` — per Workflow step 6, that file still follows
  the single-run schema above, populated from this reconciled data (with
  each finding's confirmation status folded into its presentation) rather
  than from any one individual run.

## Diffing across versions: the two diff shapes

`scripts/diff_reviews.py <old> <new>` auto-detects, from what `<old>`/`<new>`
point to, which of two different diff shapes to produce:

**Deterministic diff** (`<old>`/`<new>` are two skill directories):

```json
{
  "mode": "deterministic",
  "old_path": "...", "new_path": "...",
  "compliance_errors_delta": {"old_count": 2, "new_count": 0},
  "structural_warnings_delta": {"old_count": 6, "new_count": 4},
  "security_scan": {"old_skipped": false, "new_skipped": false, "changed": false},
  "new_findings": [{"category": "Structure", "check_id": "orphaned_resource_file", "...": "..."}],
  "resolved_findings": [{"category": "Metadata", "check_id": "metadata_version_missing", "...": "..."}],
  "unchanged_findings_count": 3
}
```

**Qualitative diff** (`<old>`/`<new>` are two `<skill-name>-review.json` files):

```json
{
  "mode": "qualitative",
  "old_path": "...", "new_path": "...",
  "old_skill_name": "example-skill", "new_skill_name": "example-skill",
  "overall_verdict": {"old": "needs_work", "new": "pass_with_suggestions", "changed": true},
  "category_scores": {
    "description_and_triggering": {"old": "major", "new": "pass", "changed": true},
    "...": "..."
  },
  "new_findings": [{"category": "safety", "location": "SKILL.md:90", "...": "..."}],
  "resolved_findings": [{"category": "description_and_triggering", "...": "..."}],
  "severity_changed_findings": [
    {"category": "writing_style_and_content", "location": "SKILL.md:42",
     "old_severity": "major", "new_severity": "minor", "issue": "..."}
  ],
  "unchanged_findings_count": 1
}
```

**Field notes:**
- `new_findings`/`resolved_findings`: grouped by `check_id` + `location` in
  deterministic mode, by `category` + `location` in qualitative mode (same
  matching rationale as the self-consistency reconciler above) — falling
  back to `issue` text instead of `location` when a finding has none, so
  two distinct no-location findings under the same check/category don't
  collide into a single diff entry.
- `severity_changed_findings` only exists in qualitative mode. The
  deterministic layer can't have it: a check's severity is fixed per
  `check_id` by `severity_config.yaml`, the same for every occurrence,
  while a qualitative finding's severity is a per-instance judgment call
  that can genuinely change between two versions of the same underlying
  issue (e.g. downgraded from `major` to `minor` after a partial fix).
- Mixing one directory and one `.json` file is rejected with a
  `fatal_error` — there's no shared schema to diff them against.
- `--fail-on-new` exits 1 iff `new_findings` is non-empty — for a CI gate
  that should block a PR only on regressions it actually introduced, not
  on pre-existing findings.
