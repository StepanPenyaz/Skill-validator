---
name: diff-new-skill
description: Cleans up and validates uploaded documents before filing them. Use this whenever the user uploads a document that needs validation or cleanup.
allowed-tools: ["WebSearch"]
metadata:
  version: "1.1.0"
---

# Diff New Skill

Deliberately mirrors an "after" version, for testing
`scripts/diff_reviews.py`'s deterministic mode against
`tests/fixtures/diff-old-skill/` (the "before" version). Fixes some issues
from the old version and introduces one genuinely new one:

- description now has a trigger cue and is well over 8 words (fixed).
- metadata.version is now set (fixed).
- unexplained hard-directive language below (carried over unchanged).
- a web-search capability is declared but never used below (carried over
  unchanged).

## Instructions

You MUST always validate the input. NEVER skip this step.
