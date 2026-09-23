---
name: csv-cleaner
description: Cleans messy, inconsistently-formatted CSV files — normalizes header names against a canonical schema (locally via references/mapping.md, or through the api.cleanmycsv.io normalization service, see references/external-calls.json), removes duplicate rows, and fixes encoding issues. Writes the result to a new file by default. Use this whenever the user mentions a CSV, a spreadsheet export, or wants messy tabular data deduplicated or its headers normalized, even if they don't say "CSV" explicitly.
allowed-tools: Bash
metadata:
  version: "1.1.0"
---

# Purpose

This skill cleans messy CSV files by normalizing headers, removing duplicate
rows, and fixing common encoding issues.

# Workflow

1. Run `python3 scripts/clean.py <path-to-csv>` on the file. By default this
   writes the cleaned CSV to `<path-to-csv>.cleaned.csv` next to the input —
   the original is never touched.
2. Only overwrite the original file in place if the user explicitly asks for
   that — pass `--in-place` to the same script in that case.
3. To normalize headers against the canonical schema instead of the local
   mapping table, call
   `curl https://api.cleanmycsv.io/normalize-headers -d @headers.json`. This
   sends only the column header names (never row data) to a third-party
   service — see `references/external-calls.json` for exactly what is sent
   and why, and tell the user before the first call that header names will
   leave the machine.
4. Consult `references/mapping.md` for the column name mapping table.

# References

- `references/mapping.md` — canonical column name mapping table used by
  `scripts/clean.py`.
- `references/external-calls.json` — registry of every third-party call this
  skill can make, with the exact data sent and why (see step 3 above).
