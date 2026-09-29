---
description: Static structure check of a skill (SKILL.md vs preferred-structure.md). Runs scripts only, no Claude session logic.
argument-hint: <path-to-skill-directory>
---

Run the static skill review for the skill at `$ARGUMENTS`.

This command is fully automatic. Do not read or judge the skill yourself, and do not start a subagent. Only run the scripts.

1. If `$ARGUMENTS` is empty or is not a directory with a `SKILL.md`, stop and ask the user for the skill path.
2. Run this command (it overwrites the previous report):

   ```bash
   python skill-eval/scripts/generate_static_report.py "$ARGUMENTS" --out "$ARGUMENTS/static_report/static_report.md"
   ```

3. Show the user the counts line from the report (blockers, warnings, info) and the path of the report file.
4. Do not fix anything unless the user asks.

The report answers one question: does `SKILL.md` follow the rules in `skill-eval/references/preferred-structure.md`?
