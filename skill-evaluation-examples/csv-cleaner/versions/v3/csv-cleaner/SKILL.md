---
name: csv-cleaner
description: Cleans messy, inconsistently-formatted CSV files — normalizes header casing/whitespace automatically, and maps header names to a canonical schema either locally (Claude applies references/mapping.md's table by hand — see Workflow step 4) or through the api.cleanmycsv.io normalization service (see references/external-calls.json); removes duplicate rows; and coerces the file to UTF-8, replacing any bytes that can't be decoded with a placeholder character (source-encoding detection/repair, e.g. Latin-1 or Windows-1252 recovery, isn't attempted). Writes the result to a new file by default. Use this whenever the user mentions a CSV, a spreadsheet export, or wants messy tabular data deduplicated or its headers normalized, even if they don't say "CSV" explicitly.
allowed-tools: Bash
metadata:
  version: "1.2.0"
---

# Purpose

This skill cleans messy CSV files by normalizing header casing/whitespace and
(optionally) mapping headers to a canonical schema, removing duplicate rows,
and coercing the file to UTF-8 — replacing bytes that can't be decoded rather
than repairing the source encoding.

# Workflow

1. Run `python3 scripts/clean.py <path-to-csv>` on the file. By default this
   writes the cleaned CSV to `<path-to-csv>.cleaned.csv` next to the input —
   the original is never touched.
2. Only overwrite the original file in place if the user explicitly asks for
   that — pass `--in-place` to the same script in that case.
3. To normalize headers against the canonical schema instead of applying the
   local mapping table by hand (step 4), write the input file's header names
   to a temp `headers.json` as `{"headers": ["email", "full name", "zip"]}`,
   then call
   `curl https://api.cleanmycsv.io/normalize-headers -d @headers.json`. This
   sends only the column header names (never row data) to a third-party
   service — see `references/external-calls.json` for exactly what is sent
   and why, and tell the user before the first call that header names will
   leave the machine.
4. If the user doesn't want header names sent to the external service (step
   3), apply `references/mapping.md`'s table yourself instead: for each
   header in the cleaned output that matches a listed variant, rename it to
   the corresponding canonical name, then re-save the file.

# References

- `references/mapping.md` — canonical column name mapping table used by
  `scripts/clean.py`.
- `references/external-calls.json` — registry of every third-party call this
  skill can make, with the exact data sent and why (see step 3 above).
