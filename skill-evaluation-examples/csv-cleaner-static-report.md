# Static Check Report: csv-cleaner

0 blocker(s), 7 warning(s), 1 info-level suggestion(s).

## Metadata

| What's Wrong | Severity | Suggested Fix |
|---|---|---|
| Description is only 4 words — the sole triggering signal Claude sees before deciding to consult the skill. | Warning | Expand the description to state both what the skill does and when to use it. |
| Description doesn't contain an obvious 'when to use this' cue (e.g. 'when', 'use this whenever...'). | Warning | Add an explicit when-to-use cue, e.g. 'Use this whenever...'. |

## Structure

| What's Wrong | Severity | Suggested Fix |
|---|---|---|
| `references\legacy_notes.md` — Bundled resource file is never mentioned by name in the SKILL.md body. | Warning | Add a pointer to this file by name somewhere in the body, or remove it if unused. |
| 2 of 8 recommended SKILL.md sections found — missing: When to Use, When NOT to Use, Rules, Decision Guidelines, Validation, References. | Info | Optional: consider restructuring around references/preferred-structure.md's outline. Not every skill needs all eight sections. |

## Permissions & Tool Usage

| What's Wrong | Severity | Suggested Fix |
|---|---|---|
| Tool 'Bash' is declared in allowed-tools but never referenced in the SKILL.md body. | Warning | Remove the unused tool from allowed-tools, or reference it in the body if it is actually needed. |

## Security

| What's Wrong | Severity | Suggested Fix |
|---|---|---|
| `SKILL.md:10` — MUST/NEVER directive: "2. You MUST always overwrite the original file with the cleaned version â€”" | Warning | Review against rubric.md's guidance: add rationale, or recommend a companion enforcement hook if this protects against real harm. |
| `SKILL.md:11` — MUST/NEVER directive: "NEVER save a backup copy, that just wastes disk space." | Warning | Review against rubric.md's guidance: add rationale, or recommend a companion enforcement hook if this protects against real harm. |
| External host referenced but never mentioned in the frontmatter description: api.cleanmycsv.io | Warning | Mention this host in the description, or remove/replace the call if it's unexpected. |
