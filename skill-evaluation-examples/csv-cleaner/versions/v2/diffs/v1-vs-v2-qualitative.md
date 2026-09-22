# Diff: csv-cleaner -> csv-cleaner (qualitative)

Overall verdict: blocked -> pass (changed)

## Category scores

| Category | Old | New | Changed |
|---|---|---|---|
| compliance | pass | pass |  |
| description_and_triggering | major | pass | yes |
| safety | blocker | pass | yes |
| structure_and_progressive_disclosure | minor | pass | yes |
| writing_style_and_content | minor | pass | yes |

0 new finding(s), 5 resolved, 0 severity-changed, 0 unchanged.

## Resolved findings

| Category | Severity | Issue | Location |
|---|---|---|---|
| description_and_triggering | major | Description states only WHAT the skill does, in 4 words, with no 'when to use' cue and no mention that it overwrites the file in place or calls an external service. Per rubric.md, a flat description with no when-clause is a Major finding — it will under-trigger. | frontmatter.description |
| safety | major | MUST always overwrite the original file, NEVER keep a backup — on an irreversible operation, justified only by disk-space savings rather than weighed against the data-loss risk if the dedup logic in scripts/clean.py drops a row that only looks like a duplicate. This directive removes the user's only safety net rather than protecting against harm, which is the opposite of what rubric.md's hard-directive guidance expects to find here. | SKILL.md:10-11 |
| safety | blocker | The skill posts CSV header data to api.cleanmycsv.io — an external host that is never named in the frontmatter description and never disclosed to the user before the call. Confirmed against the real text: the host appears nowhere else in the skill, there's no opt-out, and the description gives no hint that any data leaves the machine. This matches the rubric's exfiltration bar: 'Flag anything that could compromise system security, exfiltrate data, or enable unauthorized access as a Blocker, regardless of how the skill frames its own purpose.' | SKILL.md:15 |
| structure_and_progressive_disclosure | minor | orphaned_resource_file candidate confirmed as real: legacy_notes.md is never pointed to anywhere in the SKILL.md body, by name or indirectly (no `python -m`-style reference either) — checked the full text, there's no pointer. | references/legacy_notes.md |
| writing_style_and_content | minor | Step 2 crams two independent instructions (overwrite behavior, backup prohibition) onto one line, with the rationale trailing as an afterthought — easy to skim past the safety-relevant part. | SKILL.md:10-11 |
