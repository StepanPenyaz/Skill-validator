---
name: good-skill
description: Formats and cleans up CSV exports — fixing headers, removing blank rows, standardizing date formats. Use this whenever the user mentions a CSV, spreadsheet export, or wants tabular data cleaned or reformatted, even if they don't say "CSV" explicitly.
---

# Good Skill

This is a minimal fixture skill used to test that `structural_check.py`
reports zero compliance errors and zero structural warnings on a
well-formed skill.

## Steps

1. Read the input file with `view`.
2. Clean the data following `references/format-guide.md`.
3. Write the cleaned output.

See `references/format-guide.md` for the exact formatting rules.
