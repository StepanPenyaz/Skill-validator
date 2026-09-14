---
name: diff-old-skill
description: Helps with documents.
allowed-tools: ["WebSearch"]
---

# Diff Old Skill

Deliberately mirrors a "before" version, for testing
`scripts/diff_reviews.py`'s deterministic mode against
`tests/fixtures/diff-new-skill/` (the "after" version). Known issues, some
fixed in the new version and some carried over unchanged:

- description has no trigger cue and is under 8 words (fixed in new).
- no metadata.version is set (fixed in new).
- unexplained hard-directive language below (carried over unchanged).
- a web-search capability is declared but never used below (carried over
  unchanged).

## Instructions

You MUST always validate the input. NEVER skip this step.
