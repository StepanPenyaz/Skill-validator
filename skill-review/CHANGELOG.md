# Changelog

All notable changes to the `skill-review` skill are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
versioning follows [SemVer](https://semver.org/).

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
