---
name: good-skill
description: Formats and cleans up CSV exports — fixing headers, removing blank rows, standardizing date formats. Use this whenever the user mentions a CSV, spreadsheet export, or wants tabular data cleaned or reformatted, even if they don't say "CSV" explicitly.
metadata:
  version: "1.0.0"
---

# Good Skill

This is a minimal fixture skill used to test that `structural_check.py`
reports zero compliance errors and zero structural warnings on a
well-formed skill — including the two soft (Info-level) checks that are
easy to overlook on an otherwise-minimal skill: `metadata.version` and the
`references/preferred-structure.md` section outline below.

## Purpose

Clean up CSV exports: fix headers, remove blank rows, standardize date
formats.

## When to Use

Whenever the user mentions a CSV, spreadsheet export, or wants tabular data
cleaned or reformatted, even if they don't say "CSV" explicitly.

## When NOT to Use

Not for spreadsheet formats other than CSV, and not for anything beyond
formatting — this skill doesn't analyze or summarize the data.

## Workflow

1. Read the input file with `view`.
2. Clean the data following `references/format-guide.md`.
3. Write the cleaned output.

## Rules

- Never drop a row silently — if a row can't be cleaned, flag it instead of
  removing it.

## Decision Guidelines

If the input isn't valid CSV, say so rather than guessing at a delimiter.

## Validation

Confirm the output has the same row count as the input, minus any rows
explicitly flagged as dropped.

## References

See `references/format-guide.md` for the exact formatting rules.
