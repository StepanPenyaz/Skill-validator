---
name: csv-cleaner
description: >-
  Cleans messy, inconsistently-formatted CSV files — normalizes header
  casing/whitespace, removes duplicate rows, and coerces the file to UTF-8,
  replacing any bytes that can't be decoded with a placeholder character
  (source-encoding detection/repair, e.g. Latin-1 or Windows-1252 recovery,
  isn't attempted). Writes the result to a new file by default. If the user
  also wants headers renamed to a canonical schema, that's a separate
  opt-in step, not done by default — locally via scripts/clean.py's --map
  flag against references/mapping.json (the default when mapping is
  wanted — nothing leaves the machine), or through the api.cleanmycsv.io
  service only if the user specifically asks for that instead (see
  references/external-calls.json). Use this whenever the user mentions a
  CSV, a spreadsheet export, or wants messy tabular data deduplicated or
  its headers normalized, even if they don't say "CSV" explicitly.
allowed-tools: Bash
metadata:
  version: "1.3.0"
---

# Purpose

This skill cleans messy CSV files by normalizing header casing/whitespace,
removing duplicate rows, and coercing the file to UTF-8 — replacing bytes
that can't be decoded rather than repairing the source encoding. Renaming
headers to a canonical schema is a separate, optional step, only done when
the user actually asks for it.

# Workflow

1. Run `python3 scripts/clean.py <path-to-csv>` on the file. This
   normalizes header casing/whitespace and drops exact-duplicate rows. By
   default it writes the cleaned CSV to `<path-to-csv>.cleaned.csv` next to
   the input — the original is never touched.
2. Only overwrite the original file in place if the user explicitly asks
   for that — pass `--in-place` to the same command.
3. Only if the user also wants headers renamed to a canonical schema, add
   `--map references/mapping.json` to the command, e.g.
   `python3 scripts/clean.py <path-to-csv> --map references/mapping.json`.
   This looks up each already-normalized header (step 1's casing/whitespace
   pass runs first) in the table and renames matches to their canonical
   name; anything not listed is left as-is. This is the default way to do
   canonical-schema mapping — don't reach for step 4's external service
   unless the user asks for that specifically. Don't run this step at all
   if the user didn't ask for canonical-schema mapping; step 1's output
   already has clean headers on its own.
4. Only if the user explicitly wants header renaming done through the
   external `api.cleanmycsv.io` service instead of the local table above:
   write the input file's header names to a temp `headers.json` as
   `{"headers": ["email", "full name", "zip"]}`, then call
   `curl https://api.cleanmycsv.io/normalize-headers -d @headers.json`. This
   sends only the column header names (never row data) to a third-party
   service — see `references/external-calls.json` for exactly what is sent
   and why, and tell the user before the first call that header names will
   leave the machine.

# References

- `references/mapping.json` — canonical column name mapping table consumed
  by `scripts/clean.py --map` (step 3 above).
- `references/external-calls.json` — registry of every third-party call this
  skill can make, with the exact data sent and why (see step 4 above).
