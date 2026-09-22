# Diff: `skill-evaluation-examples\csv-cleaner\versions\v1\csv-cleaner` -> `skill-evaluation-examples\csv-cleaner\versions\v2\csv-cleaner` (deterministic)

Compliance errors: 0 -> 0  
Structural warnings: 8 -> 2  

1 new finding(s), 7 resolved, 1 unchanged.

## New findings

| Check | Severity | Issue | Location |
|---|---|---|---|
| preferred_structure_sections_missing | Info | 3 of 8 recommended SKILL.md sections found — missing: When to Use, When NOT to Use, Rules, Decision Guidelines, Validation. |  |

## Resolved findings

| Check | Severity | Issue | Location |
|---|---|---|---|
| description_no_trigger_cue | Warning | Description doesn't contain an obvious 'when to use this' cue (e.g. 'when', 'use this whenever...'). |  |
| description_too_short | Warning | Description is only 4 words — the sole triggering signal Claude sees before deciding to consult the skill. |  |
| must_never_line | Warning | MUST/NEVER directive: "2. You MUST always overwrite the original file with the cleaned version â€”" | SKILL.md:10 |
| must_never_line | Warning | MUST/NEVER directive: "NEVER save a backup copy, that just wastes disk space." | SKILL.md:11 |
| orphaned_resource_file | Warning | Bundled resource file is never mentioned by name in the SKILL.md body. | references\legacy_notes.md |
| preferred_structure_sections_missing | Info | 2 of 8 recommended SKILL.md sections found — missing: When to Use, When NOT to Use, Rules, Decision Guidelines, Validation, References. |  |
| undeclared_external_host | Warning | External host referenced but never mentioned in the frontmatter description: api.cleanmycsv.io |  |
