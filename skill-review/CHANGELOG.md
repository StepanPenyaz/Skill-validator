# Changelog

All notable changes to the `skill-review` skill are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
versioning follows [SemVer](https://semver.org/).

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
