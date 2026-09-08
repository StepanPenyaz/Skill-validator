---
name: BadSkill_v2
description: Helps with documents.
---

# Bad Skill

This is a minimal fixture skill with deliberate issues, used to confirm
`structural_check.py` catches each one:

- `name` is not kebab-case and doesn't match the folder name (`bad-skill`).
- `description` has no "when to use" trigger cue and is under 8 words.
- The instructions below reference a hardcoded personal path.
- A bundled script exists in `scripts/` but is never pointed to below (orphaned).
- Heavy unexplained MUST/NEVER usage with no rationale given.

## Instructions

You MUST always read the file at /Users/johndoe/Documents/input.txt.
You MUST NEVER skip validation. You MUST ALWAYS write output exactly as
specified. NEVER deviate from this process under any circumstances.
