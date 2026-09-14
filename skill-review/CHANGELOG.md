# Changelog

All notable changes to the `skill-review` skill are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
versioning follows [SemVer](https://semver.org/).

## [1.9.0] — 2026-09-14

### Added
- `scripts/diff_reviews.py` (new file): folds the previously-external,
  by-hand version-diffing process into skill-review itself, per
  `SKILL.md`'s long-standing (but until now unfulfilled) claim that the
  JSON output is "designed to be diffed across versions." Auto-detects two
  modes from what its `<old>`/`<new>` arguments point to:
  - Two skill directories -> deterministic diff. Runs
    `structural_check.py` against each and diffs `compliance_errors`,
    `structural_warnings`, and findings (grouped by `check_id` + `location`).
    No model call.
  - Two `<skill-name>-review.json` files (the qualitative output) -> diffs
    `overall_verdict`, `category_scores`, and findings (grouped by
    `category` + `location`), including `severity_changed_findings` — a
    severity change on a finding that persists across versions, which only
    exists in this mode since deterministic severities are fixed per
    `check_id`, not assigned per instance.
  - `--markdown` for a human-readable table (mirrors
    `generate_static_report.py`'s style); `--fail-on-new` exits 1 only if
    `<new>` introduces a finding `<old>` didn't have, so a CI gate can
    block a PR on regressions it actually introduced without also blocking
    on every pre-existing finding; `--force-security-scan` passes through
    to `structural_check.py` in deterministic mode; `--out` writes to a file.
  - Mixing one directory and one `.json` file is rejected with a
    `fatal_error`.
- `tests/fixtures/diff-old-skill/` + `diff-new-skill/`: a "before"/"after"
  pair of skill directories exercising the deterministic mode (1 new
  finding, 3 resolved, 3 unchanged).
- `tests/fixtures/version-diff/`: a "before"/"after" pair of
  `<skill-name>-review.json` files exercising the qualitative mode,
  including one finding's severity downgrading from `major` to `minor`.
- `references/schema.md`: new "Diffing across versions: the two diff
  shapes" section documenting both output shapes.
- 5 new checks in `tests/run_regression.py` covering both modes,
  `--fail-on-new`'s exit code in both directions, and the mixed-input
  rejection.

## [1.8.0] — 2026-09-14

### Added
- `tests/run_regression.py` (new file): skill-review's own regression
  suite. Runs `structural_check.py` and `reconcile_reviews.py` against
  every fixture under `tests/fixtures/` (plus skill-review's own
  directory) exactly as documented in this README's "Local testing"
  section, and asserts the result — instead of a human re-running each
  command by hand and eyeballing the output before every change to
  `structural_check.py`, `severity_config.yaml`, `reconcile_reviews.py`, or
  a fixture. Plain assertions over subprocess calls to the real CLI
  entrypoints; no test-framework dependency added.
- `.github/workflows/tests.yml` (repo root, new file): runs
  `tests/run_regression.py` and a packaging sanity check
  (`scripts/package_skill.py`) on every push and pull request.
- `findings[].check_id` (new field) on `structural_check.py`'s output: the
  same stable key used in `references/severity_config.yaml`, now also
  returned per finding so code (including the new regression suite) can
  match on a specific check without depending on free-text `issue`/
  `suggestion` wording, which can be reworded without notice.

### Fixed
- `tests/fixtures/good-skill/`: added `metadata.version` and the 8
  `references/preferred-structure.md` section headings. It previously
  reported 2 structural warnings despite the README claiming (and this
  repo's own regression suite now enforcing) that it reports zero —
  neither warning was ever actually exercising a real check regression, so
  this was silent doc/fixture drift rather than a caught bug.
- `tests/fixtures/bad-skill/SKILL.md`: its own intro named
  `scripts/helper.py` by filename while describing a *different* planted
  issue (the dangerous-shell-pattern one), which accidentally satisfied
  `orphaned_resource_file`'s "referenced by name somewhere in the body"
  check — so despite another bullet in the same intro claiming the script
  is orphaned, that check never actually fired. Reworded to describe the
  script without naming it, so the fixture matches its own documentation.

## [1.7.0] — 2026-09-14

### Added
- Self-consistency for the qualitative pass: `SKILL.md` Workflow step 6
  (new) has Claude produce N independent qualitative review runs
  (`<skill-name>-review-run<N>.json`, N=3 by default) instead of treating a
  single pass as the final verdict, for reviews where noise is costly (a
  CI gate, a version diff, or when the user explicitly wants higher
  confidence).
- `scripts/reconcile_reviews.py` (new file): deterministic, model-free
  aggregation over those N run files. Groups findings across runs by
  `(category, location)`, reports each one's agreement count and a
  consensus severity (majority vote, ties broken toward the more severe
  value), and recomputes `overall_verdict`/`category_scores` from the
  reconciled data using the same derivation rule as a single run.
  `--threshold` overrides the default simple-majority confirmation bar;
  `--out` writes to a file instead of stdout.
- `tests/fixtures/consistency-runs/`: three synthetic, independent review
  runs of one hypothetical skill (`example-skill`), used as both a worked
  example and a regression fixture for `reconcile_reviews.py`. Deliberately
  includes a one-off `blocker`-severity finding in run 1 only — the exact
  failure mode from the issue this feature addresses, where that single
  run's `overall_verdict` is `blocked` but the 3-run consensus correctly
  settles on `needs_work` once the finding is recognized as unconfirmed
  (1 of 3 runs).
- `references/schema.md`: new "Self-consistency: the reconciled-review
  shape" section documenting `reconcile_reviews.py`'s output schema,
  distinct from the single-run `<skill-name>-review.json` schema.

## [1.6.0] — 2026-09-14

### Added
- Cost-conditional security scanning: the dangerous-shell-pattern,
  prompt-injection, and undeclared-host scans (`scan_patterns` over
  `DANGEROUS_SHELL_PATTERNS`/`PROMPT_INJECTION_PATTERNS` and
  `find_undeclared_external_hosts`) now skip by default for a skill whose
  `allowed-tools` frontmatter and SKILL.md body declare/reference no
  shell-executing (`Bash`) or network-capable (`WebFetch`/`WebSearch`/any
  `mcp__*`) tool — measured to add roughly 2x cost with zero benefit on
  skills that have no way to act on what those scans would find.
  Hardcoded-secret and prohibited-action-phrase scanning are never gated;
  both matter regardless of the skill's own tool access.
- `metrics.security_scan` (new field): `{skipped, forced, checks_skipped,
  reason}`, always present so the skip is auditable rather than silent —
  check `skipped` before reading an empty `*_candidates` list as "scanned,
  found nothing" instead of "didn't look."
- `--force-security-scan` flag on both `structural_check.py` and
  `generate_static_report.py`: bypasses the gate and always runs the full
  scan, for when the heuristic looks wrong for a particular skill.
  `generate_static_report.py`'s Markdown output now leads with a
  blockquote note when the scan was skipped.
- `structural_check.py`'s `compute_tool_usage()` now also returns the raw
  referenced-tool set (previously computed but not returned), reused by
  the new `has_shell_or_network_capability()` gate function.

## [1.5.0] — 2026-09-08

### Added
- `references/severity_config.yaml` (new file): externalizes every check's
  severity (Blocker/Warning/Info) into an editable `check_id -> {what_is_wrong,
  severity}` table. Editing a `severity` value there changes what any future
  validation run reports — for every skill — with no code changes.
- `README.md` (root) and `skill-review/README.md`: substantially expanded —
  purpose, the full current validation checklist organized by category
  (Metadata / Structure / Permissions & Tool Usage / Security), concrete
  usage examples for both scripts, and how to retune severity via the new
  config file. Root README now has a short pointer section describing
  `skill-review` instead of only a generic repo-layout blurb.

### Changed
- `scripts/structural_check.py`: `add_finding()` now takes a `check_id`
  instead of a literal severity string, and resolves severity via a new
  `load_severity_config()` that reads `references/severity_config.yaml`
  (path resolved relative to the script file, so this keeps working
  regardless of caller cwd and stays self-contained when the skill is
  packaged/distributed standalone). `run_checks()` loads and validates the
  config before running any check, returning `fatal_error` immediately on a
  missing file, YAML parse error, or an invalid/missing severity value —
  fails fast and clearly rather than defaulting silently or crashing with a
  raw traceback. `scripts/generate_static_report.py` required no changes —
  it already just renders whatever severity ends up on each finding.

## [1.4.0] — 2026-09-08

### Added
- `scripts/structural_check.py`: every check now also records a structured
  finding — `{category, severity, issue, suggestion, location}` — in a new
  `result["findings"]` array, in addition to the existing
  `compliance_errors`/`structural_warnings`/`metrics` (now derived from
  `findings` rather than hand-appended, for a single source of truth).
  `category` is one of Metadata / Structure / Permissions & Tool Usage /
  Security. `severity` is a fixed, per-check-type Blocker/Warning/Info scale
  — **distinct from** the qualitative rubric's Minor/Major/Blocker/Pass
  scale used in the final `<skill-name>-review.json`/`.md`; the two are not
  interchangeable. Internals also refactored: `main()`'s check logic moved
  into a new `run_checks(skill_path)` function that other scripts can import
  and call directly (returns `{"fatal_error": ...}` instead of exiting).
- `scripts/generate_static_report.py` (new file): renders `findings` as a
  human-readable Markdown report — one table per category, each row showing
  what's wrong, its severity, and a suggested fix (one row per occurrence,
  not aggregated). `python scripts/generate_static_report.py <skill_dir>
  [--out <path>]`. This is still the deterministic Linter stage — no
  qualitative judgment is applied, and it's explicitly not a substitute for
  the full `<skill-name>-review.md` produced by the qualitative Static
  Quality pass (SKILL.md Steps 3-5).
- `SKILL.md` Step 2: points at the new script as an optional fast, static-
  only view when that's what the user actually wants.

### Fixed
- `scripts/generate_static_report.py`: explicitly reconfigures stdout/stderr
  to UTF-8. Without this, printing the report on Windows used the console's
  default codepage (commonly cp1252), which can't represent characters like
  em dashes or the "…redacted…" marker used for hardcoded-secret findings —
  found by round-tripping the report through `--out` and comparing to
  stdout.

## [1.3.0] — 2026-09-08

### Fixed
- `scripts/structural_check.py`: resource-directory enumeration
  (`resource_file_count`, `resource_dir_file_counts`,
  `orphaned_resource_files`) and the new security pattern scans now both
  reuse the existing `PACKAGING_EXCLUDE_DIRS` exclusion (plus `.pyc`/`.pyo`),
  the same list `package_skill.py` strips before packaging. Previously a
  `scripts/__pycache__/*.pyc` build artifact left over from running the
  script locally was being counted as a bundled resource, flagged as
  orphaned, and scanned for dangerous-pattern/secret matches — caught by
  running the checker against this skill's own directory.

### Added
- `scripts/structural_check.py`:
  - Metadata: `SKILL.md` filename case check (hard error if not exactly
    `SKILL.md`); `metadata.version` presence check (warning).
  - Structure: `metrics.resource_dir_file_counts` (per-directory file counts
    for `scripts/`, `references/`, `assets/`, alongside the existing
    aggregate `resource_file_count`); `metrics.preferred_structure_sections`
    reporting coverage of the new recommended section outline (soft signal
    only, never a compliance error).
  - Permissions: `metrics.declared_tools`,
    `metrics.tools_declared_but_unreferenced`, and
    `metrics.tools_referenced_but_undeclared` — cross-checks `allowed-tools`
    frontmatter against tool/MCP references in the SKILL.md body (candidates,
    same treatment as `orphaned_resource_files`).
  - Security: hardcoded secret/credential detection
    (`metrics.hardcoded_secret_candidates`) — reported as hard
    `compliance_errors` with the matched value redacted; dangerous shell
    pattern detection (`metrics.dangerous_shell_pattern_candidates`);
    prompt-injection/instruction-override phrasing detection
    (`metrics.prompt_injection_phrase_candidates`); prohibited high-risk
    action phrasing detection (`metrics.prohibited_action_phrase_candidates`);
    undeclared external host detection (`metrics.undeclared_external_hosts`).
    All security scans cover both the SKILL.md body and every file under
    `scripts/`.
- `references/preferred-structure.md` (new file) — a recommended 8-section
  SKILL.md outline (Purpose, When to Use, When NOT to Use, Workflow, Rules,
  Decision Guidelines, Validation, References), kept separate from
  `rubric.md`/`schema.md` so it can be revised independently.
- `references/rubric.md`: short addition under Safety directing the reviewer
  to confirm the new candidate metrics against real context before reporting
  them as findings — same "candidate, not verdict" treatment already used for
  `orphaned_resource_files` and `must_never_lines`.
- `references/schema.md`: documented the new `metrics` fields and noted that
  `compliance_errors` can now include redacted hardcoded-secret findings.

### Notes
- Deliberately out of scope: "overly broad permissions relative to stated
  purpose" and "silent scope creep" (body actions vs. description promises)
  are not implemented anywhere in this skill — both require semantic
  judgment beyond what a fast, regex-based linter can reliably do, and
  turning them into a new qualitative rubric category wasn't taken on either.
  `rubric.md`'s existing "Principle of Lack of Surprise" already covers
  adjacent ground for the qualitative pass.

## [1.2.0] — 2026-09-08

### Added
- `scripts/structural_check.py`: new `metrics.must_never_lines` — every
  MUST/NEVER line in the SKILL.md body, with line number and text, instead
  of just the aggregate counts in `metrics.imperative_marker_counts`.
- `references/rubric.md`: new Safety guidance, "Hard directives that need
  enforcement, not just prose" — for each `must_never_lines` entry, judge
  whether it protects against real harm (data loss, security bypass,
  unauthorized access, exfiltration) that a model could be talked past
  through prose alone. If so, recommend pairing it with a project-level
  Claude Code hook for deterministic enforcement (a skill can't configure
  its own hooks, so the prose instruction stays — this adds a
  recommendation, it doesn't replace anything). Stylistic/low-stakes
  MUST/NEVERs are left alone.
- `SKILL.md` Step 3: now directs the reviewer to walk `must_never_lines`
  against that rubric guidance.

## [1.1.0] — 2026-09-08

### Fixed
- `scripts/structural_check.py`: the "exactly one SKILL.md" packaging check
  now ignores dev-only directories (`tests/`, `.git`, `__pycache__`, `dist`,
  `node_modules`, `.pytest_cache`) instead of counting fixture skills'
  `SKILL.md` files as compliance blockers. This fixes a false-positive
  `blocked` verdict this skill produced against itself once its own test
  fixtures carry their own `SKILL.md`.
- `SKILL.md` Step 5: added a fallback for saving output files when
  `/mnt/user-data/outputs/` isn't a valid path in the current environment
  (e.g. a local Claude Code session) — previously there was no instruction
  for that case.

### Changed
- Moved `fixtures/` to `tests/fixtures/` to match the layout `README.md`
  already documented (the two had drifted out of sync).
- `README.md`: packaging instructions now point at the repo-level
  `../scripts/package_skill.py`, which actually exists and excludes the
  same dev-only directories `structural_check.py` now ignores. Replaces the
  old "vendor a copy if unavailable" placeholder.

## [1.0.0] — 2026-09-08

### Added
- Initial release.
- `scripts/structural_check.py`: deterministic compliance and structural
  checker — frontmatter validation (name/description rules, allowed keys,
  single-SKILL.md rule), line-count metrics, resource-directory inventory,
  orphaned bundled-resource detection, large-reference-file TOC check,
  hardcoded-path (portability) detection, imperative-marker (MUST/NEVER/
  ALWAYS) counts.
- `references/rubric.md`: qualitative scoring rubric across four
  categories — description & triggering quality, structure & progressive
  disclosure, writing style & content quality, safety.
- `references/schema.md`: JSON output schema for the review scorecard
  (`<skill-name>-review.json`) and the generated markdown report.
- `SKILL.md`: end-to-end review workflow — locate skill, run deterministic
  check, confirm script-flagged candidates against actual text, qualitative
  rubric pass, produce JSON + markdown outputs.

### Notes
- No runtime/execution-based evaluation is performed by this skill — it is
  purely static. See the broader Claude Code Skill Evaluation plan for the
  execution-based benchmark layer this is meant to complement.
