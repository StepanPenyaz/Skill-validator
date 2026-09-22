# Plan: three new skill-review checks (evaluation criteria doc, test coverage, external-call registry)

> **Status: proposed, not yet implemented.** This document captures the agreed design for three
> new `skill-review` checks before any code is written, so the approach can be reviewed
> independently of the implementation diff.

## Context

The user reviewed the `csv-cleaner` demo (`skill-evaluation-examples/csv-cleaner/`, PR #42) and
wants `skill-review`'s checking taxonomy extended with three things it currently has no concept
of:

1. Every skill under review must ship a document describing its own evaluation criteria — and
   its absence must be a **hard precondition failure**, not just advice, for both `skill-review`
   and `skill-eval` (the latter already refuses to proceed on any Blocker, so this reuses that
   existing gate rather than adding new plumbing to `skill-eval`).
2. A skill that bundles executable `scripts/` but no `tests/` should be flagged by `skill-review`
   — exactly the gap `csv-cleaner` currently has and that the user noticed by hand.
3. Any external host a skill's `SKILL.md`/`scripts/` actually calls (e.g. the undisclosed
   `curl https://api.cleanmycsv.io/...` finding from the earlier full review) must be declared in
   a `references/*.json` registry with `key`/`value`/`description` fields per entry, and that
   registry must itself be pointed to from `SKILL.md`.

All three follow the repo's existing two-layer pattern: a cheap, deterministic **candidate**
signal in `structural_check.py` (gate mode) that the qualitative pass in `references/rubric.md`
then confirms or dismisses (full review mode) — same as `orphaned_resource_file`,
`undeclared_external_host`, etc. already work.

## 1. Evaluation-criteria document

- **Convention:** a required root-level file `<skill-root>/EVALUATION_CRITERIA.md`, sibling to
  `SKILL.md` — matches the existing root-level-file convention each skill already uses for
  `README.md`/`CHANGELOG.md` (rather than burying it in `references/`, which is optional-by-design
  in this taxonomy).
- **New reference doc:** `skill-review/references/evaluation-criteria-format.md` (parallel to
  `preferred-structure.md`) suggesting what belongs in it — success criteria, non-goals,
  representative task prompts (deliberately worded to dovetail with `skill-eval`'s
  `references/task-authoring.md`, so a skill author writes this once and both tools benefit — no
  code coupling, just a doc cross-reference).
- **`structural_check.py` — `check_evaluation_criteria_doc()`** (new function, called alongside
  `check_metadata_version`):
  - `evaluation_criteria_missing` — **Blocker** — file absent (or present under the wrong case,
    same Windows case-insensitivity concern `check_skill_md_filename_case` already handles).
  - `evaluation_criteria_too_thin` — **Warning** — file exists but is under ~30 words (mirrors
    `description_too_short`'s heuristic).
  - New metric: `metrics["evaluation_criteria_doc_present"]`.
- **Category:** new `CATEGORY_EVALUATION = "Evaluation Readiness"` constant (shared with #2 below).
  `generate_static_report.py` hardcodes `CATEGORY_ORDER` (confirmed by exploration:
  `skill-review/scripts/generate_static_report.py` lines 37-42) — a finding under an
  unlisted category is silently dropped from the Markdown report though it stays in the JSON, so
  the new constant must be added to that list too.
- **Blocker severity is a deliberate taxonomy broadening**, worth calling out: `severity_config.yaml`'s
  own doc-comment currently defines Blocker as "will fail to parse, package, or ship safely" — a
  missing criteria doc doesn't break packaging, but the user was explicit that this must gate both
  tools the same way a real compliance failure does. Reusing the existing
  Blocker → `compliance_errors` → `skill-eval` hard-stop path (rather than adding a parallel gate
  inside `skill-eval`) is the simplest way to honor that, at the cost of stretching what "Blocker"
  means. The doc-comment in `severity_config.yaml` should be updated to say so explicitly rather
  than leave it inconsistent.
- **Consequence (repo-wide retrofit):** every existing skill this repo's own regression suite
  self-checks or asserts "zero findings" on will need an `EVALUATION_CRITERIA.md` added:
  `skill-review/` itself, `skill-eval/` itself, `skill-review/tests/fixtures/good-skill/`,
  `skill-review/tests/fixtures/clean-skill-with-tricky-patterns/`, and the diff/consistency
  fixtures (`diff-old-skill`, `diff-new-skill`, `version-diff/*`, `consistency-runs/*` — exact
  extent to be determined by running `run_regression.py` and fixing what it flags). `bad-skill`
  gets the new check_id added to its expected-findings set instead (it's supposed to be missing
  things). `skill-evaluation-examples/csv-cleaner` should **not** be retrofitted with a fix — it's
  the intentional bad example, so the new Blocker becomes part of what its regenerated review
  reports show.

## 2. Test-coverage check

- **`structural_check.py` — `check_test_coverage()`** (new function, called right after
  `resource_dir_file_counts` is computed, since it needs `resource_dir_file_counts["scripts"]`):
  - Cost-gated the same way the security scans are (`has_shell_or_network_capability` /
    `security_scan.skipped` pattern) — only meaningful when the skill actually bundles a
    non-empty `scripts/` dir; a skill with no executable code has nothing to unit test
    deterministically. New metric `metrics["test_coverage"] = {"skipped": bool, "reason": ...,
    "tests_dir_present": bool, "test_file_count": N}`, mirroring `metrics["security_scan"]`'s
    shape exactly so the "skipped ≠ scanned-and-clean" distinction is visible the same way.
  - `tests_missing` — **Warning** (softer than #1, per how the user phrased this one) — fires when
    `scripts/` is non-empty and `tests/` doesn't exist or is empty.
  - Category: `CATEGORY_EVALUATION` (same new category as #1).
- **`rubric.md` addition:** full review confirms whether present tests are substantive
  (assert something real) vs. a stub — Minor if thin, Major if `scripts/` has real logic and zero
  tests, consistent with the "candidate vs. verified" treatment used everywhere else in the rubric.
- **Fixture consequence:** `bad-skill` (has `scripts/helper.py`, no `tests/`) gains
  `tests_missing` as a newly-expected check_id — exactly the extension mechanism
  `run_regression.py`'s own pattern already uses (add expected id + plant/confirm the triggering
  condition in the fixture). `clean-skill-with-tricky-patterns` (has `scripts/install.sh`) needs a
  `tests/` dir added with one real test to stay at zero findings — a natural addition to that
  fixture's documented list of "looks-risky-but-is-fine" patterns.

## 3. External-call registry

- **Convention:** `references/external-calls.json`, shape:
  ```json
  {"calls": [{"key": "cleanmycsv_normalize_headers",
              "value": "https://api.cleanmycsv.io/normalize-headers",
              "description": "Sends CSV column headers to a third-party service to normalize them."}]}
  ```
  Lives under `references/` (unlike #1) because it's genuinely optional metadata that only needs
  to exist when the skill makes external calls — it will naturally participate in the *existing*
  `orphaned_resource_file` check once present, which already covers "must be mentioned by name in
  `SKILL.md`" without inventing a second check for that half of requirement #3.
- **New reference doc:** `skill-review/references/external-calls-schema.md` documents the exact
  field names/types and gives a filled-in example, referenced from `SKILL.md`'s own References
  section.
- **`structural_check.py` changes** — extends the existing `find_undeclared_external_hosts`
  machinery (same `URL_PATTERN`, same `scannable_files`, same `run_gated_scans` cost-gate as
  `undeclared_external_host`) rather than duplicating host-extraction logic:
  - `external_calls_registry_malformed` — **Blocker**, **not** cost-gated (same "always cheap to
    check, always worth flagging" treatment as `hardcoded_secret`) — file exists but isn't valid
    JSON, isn't `{"calls": [...]}`, or an entry is missing `key`/`value`/`description`.
  - `external_calls_registry_missing` — **Warning**, cost-gated — external host(s) found but
    `references/external-calls.json` doesn't exist at all.
  - `external_call_not_in_registry` — **Warning**, cost-gated, one finding per host — registry
    exists but a called host's URL isn't covered by any entry's `value`.
  - Category: reuse `CATEGORY_SECURITY` (extends the existing `undeclared_external_host` family
    rather than adding a third category).
  - New metrics: `metrics["external_calls_registry"] = {"present": bool, "malformed": bool,
    "entries_count": N}`, `metrics["external_hosts_missing_from_registry"] = [...]`.
- **`rubric.md` addition:** extends the existing "confirm the pattern-scan candidates" bullet to
  include these two new check_ids — e.g. a registry entry can still be legitimate even if the
  `SKILL.md` mention isn't textually adjacent to the call site; full review judges whether the
  disclosure is actually clear in context, gate mode only proves the fact/entry exists.
- **Fixture consequence:** `clean-skill-with-tricky-patterns` already names an external host in
  its description (one of its existing 5 "tricky but fine" patterns) — give it a matching
  `references/external-calls.json` entry + a body pointer, as a 6th documented tricky-but-fine
  pattern. `bad-skill` gets one external call line added (it currently has none) with no matching
  registry, to exercise `external_calls_registry_missing` + `external_call_not_in_registry` via
  the same "add to `BAD_SKILL_EXPECTED_CHECK_IDS`" mechanism as everywhere else.

## Cross-cutting updates

- `skill-review/references/severity_config.yaml` — 6 new `check_id` entries (`evaluation_criteria_missing`,
  `evaluation_criteria_too_thin`, `tests_missing`, `external_calls_registry_malformed`,
  `external_calls_registry_missing`, `external_call_not_in_registry`) with severities as above.
- `skill-review/references/schema.md` — add `category_scores.evaluation_readiness` (pass/minor/major/blocker,
  same derivation rule as the other qualitative categories), the new `metrics.*` fields, and one
  example finding under the new category.
- `skill-review/references/preferred-structure.md` — one short note cross-referencing
  `EVALUATION_CRITERIA.md` as a required root-level file outside the 8-section body outline (same
  relationship `CHANGELOG.md` already has to that outline).
- `skill-review/SKILL.md` — update the frontmatter `description` to mention the new coverage area,
  bump `metadata.version` (1.9.1 → 1.10.0, minor per the project's own changelog convention for
  "new checks"), extend Workflow step 2's description of what `structural_check.py` reports and
  step 3's four rubric areas to five, add `EVALUATION_CRITERIA.md` to skill-review's own skill
  root (needed for its own self-check in `run_regression.py` to keep passing).
- `skill-review/CHANGELOG.md` — one new `## [1.10.0]` entry, `### Added`, following the existing
  verbose/rationale-heavy style.
- `skill-review/tests/run_regression.py` — extend `BAD_SKILL_EXPECTED_CHECK_IDS` with the 4
  bad-skill-triggered new ids (`evaluation_criteria_missing`, `tests_missing`,
  `external_calls_registry_missing`, `external_call_not_in_registry`); no new assertion helpers
  needed, the existing `assert_check_ids` superset check covers it.
- `skill-eval/` — add its own `EVALUATION_CRITERIA.md` (needed for its self-check), bump
  `metadata.version` patch level, and a short doc update (`SKILL.md`/`README.md`) stating the new
  prerequisite explicitly for anyone adding a target skill to evaluate — no logic changes needed
  in `skill-eval/scripts/`, since it already hard-stops on any `compliance_errors`/blocked
  qualitative verdict regardless of which check produced it.
- `skill-evaluation-examples/csv-cleaner/` (from PR #42) — **not** fixed; regenerate its four
  existing report files (`csv-cleaner-structural-check.json`, `csv-cleaner-static-report.md`,
  `csv-cleaner-review.json`, `csv-cleaner-review.md`) by re-running gate mode and redoing the
  full-review pass against the now-extended checks, so the demo visibly shows the three new
  findings (missing `EVALUATION_CRITERIA.md`, missing `tests/` despite `scripts/clean.py`,
  undisclosed `api.cleanmycsv.io` call with no `references/external-calls.json`) end to end.

## Verification (once implemented)

1. `python skill-review/tests/run_regression.py` — must pass (covers the self-check, `good-skill`,
   `bad-skill`, `clean-skill-with-tricky-patterns`, diff/consistency fixtures).
2. `python skill-eval/tests/run_regression.py` — must still pass.
3. `python scripts/package_skill.py skill-review /tmp/dist` and same for `skill-eval` — packaging
   sanity check exactly as `.github/workflows/tests.yml` runs it, confirms `EVALUATION_CRITERIA.md`
   and `references/external-calls*.md` ship correctly and `tests/` stays excluded.
4. Manually re-run `structural_check.py` / `generate_static_report.py` against
   `skill-evaluation-examples/csv-cleaner/`, redo the full-review pass by hand, and overwrite the
   4 existing report files with the new output.
5. Report the diff to the user before committing/pushing.
