# Diff: csv-cleaner -> csv-cleaner (qualitative)

Overall verdict: needs_work -> pass_with_suggestions (changed)

## Category scores

| Category | Old | New | Changed |
|---|---|---|---|
| compliance | pass | pass |  |
| description_and_triggering | major | pass | yes |
| safety | pass | pass |  |
| structure_and_progressive_disclosure | pass | pass |  |
| writing_style_and_content | major | minor | yes |

1 new finding(s), 4 resolved, 0 severity-changed, 0 unchanged.

## New findings

| Category | Severity | Issue | Location |
|---|---|---|---|
| writing_style_and_content | minor | Step 4 (the fix for v2's F3) now gives an explicit rename instruction, but still doesn't say which mechanism performs the rename and re-save. Steps 1 and 3 both name a concrete command (`python3 scripts/clean.py ...`, `curl ...`); step 4 just says to 'apply the table yourself... rename it... then re-save the file' without saying whether that happens via a shell one-liner (which would need `Bash`, already declared), a text/file-edit tool, or manual reconstruction of the CSV. | SKILL.md:32 (Workflow step 4) |

## Resolved findings

| Category | Severity | Issue | Location |
|---|---|---|---|
| description_and_triggering | major | The description promises the skill "fixes encoding issues", but clean.py opens the file with errors="replace" (line 8), which silently substitutes U+FFFD for any byte sequence that isn't valid UTF-8 rather than detecting the file's actual source encoding (e.g. Latin-1, Windows-1252) and re-encoding it correctly. This is data loss, not a fix, and nothing in the skill warns the user it happened. | frontmatter.description / scripts/clean.py:8 |
| description_and_triggering | major | The description claims header names are normalized "against a canonical schema ... locally via references/mapping.md", but scripts/clean.py never opens or applies mapping.md — it only lowercases, strips, and underscore-replaces the header row (clean.py:12). Nothing in the Workflow instructs Claude to apply the table's renames either, so the promised local canonical-schema mapping isn't actually delivered unless the user opts into the external API (step 3). | frontmatter.description |
| writing_style_and_content | minor | Step 3's curl command reads from `headers.json` (`-d @headers.json`), but no step creates this file or defines its expected shape. | SKILL.md:23 (Workflow step 3) |
| writing_style_and_content | major | Step 4 says "Consult references/mapping.md for the column name mapping table" but gives no instruction for what to do with it — there's no mechanism in clean.py to apply it, and the step doesn't say to rename headers, when this step applies relative to step 3, or how to write the result back. As written, opening the file has no concrete follow-up action. | SKILL.md:28 (Workflow step 4) |
