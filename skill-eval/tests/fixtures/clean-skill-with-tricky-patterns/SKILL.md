---
name: clean-skill-with-tricky-patterns
description: Installs a small, checksum-verified helper CLI from get.example-tools.dev and reviews a target shell script against a short safety checklist. Use this whenever the user asks to set up the helper tool, or wants an existing shell script looked at for common mistakes like unpinned installers or overly broad file permissions.
allowed-tools: ["Bash", "Grep"]
metadata:
  version: "1.0.0"
---

# Clean Skill With Tricky Patterns

This is a precision-testing fixture: a **legitimate** skill built to contain
several patterns that surface-resemble known bad signals without actually
being defects. `structural_check.py` should report zero compliance errors
and zero structural warnings against this directory — any finding here is a
false positive and a regression in the checker, not a real issue in the
skill. Specifically, this fixture exercises:

- A `curl` download that is checksum-verified before execution, never piped
  directly into a shell — resembles the dangerous "download and pipe into
  bash" pattern at a glance, but isn't one (see `scripts/install.sh`).
- An external host (`get.example-tools.dev`) that *is* named in the
  frontmatter description, so it isn't an undeclared-host candidate.
- Ordinary lowercase "must"/"never" used as normal English words in prose
  below, rather than the all-caps imperative-directive style the checker
  actually looks for.
- `allowed-tools` that declares exactly the tools referenced in this body,
  in both directions (no over- or under-provisioning).
- A bundled resource file (`references/lint-checklist.md`) that is pointed
  to by name below, so it isn't orphaned.

## Purpose

Set up a small, trusted CLI helper on the user's machine, and review shell
scripts against a short checklist of patterns worth a second look before
running them.

## When to Use

Use this whenever the user asks to install or set up the helper tool from
get.example-tools.dev, or asks for a shell script to be checked for common
safety mistakes before they run it.

## When NOT to Use

Don't use this for installing arbitrary, unrelated software, and don't use
it as a substitute for actually reading a script the user is nervous about
— the checklist below is a prompt to look closer, not an automated verdict.

## Workflow

1. To install the helper: use the Bash tool to run `scripts/install.sh`,
   which downloads the installer and its published checksum as two separate
   files, verifies the checksum locally, and only then executes it.
2. To review a script: use the Grep tool to search the target script for
   the patterns described in `references/lint-checklist.md`, and report
   what you find along with the reasoning from that checklist.

## Rules

- Never run a downloaded installer before its checksum has been verified —
  that's what makes step 1 of the workflow safe, and it's a rule worth
  following in any script you review too.
- When reviewing a script for the user, explain *why* a pattern is worth a
  second look instead of just labeling it as bad; some of the patterns in
  the checklist are legitimate in the right context, same as they are here.

## Decision Guidelines

If the user just wants the helper tool installed, run step 1 of the
Workflow directly. If they hand you a script and ask "is this safe," walk
it against `references/lint-checklist.md` and explain each hit in context
rather than returning a bare list.

## Validation

After installing, confirm the helper CLI is on `PATH` and reports a version
string. After reviewing a script, double check that every pattern you
flagged actually appears in the checklist's reasoning — don't invent new
categories on the fly.

## References

See `references/lint-checklist.md` for the full list of patterns this
skill's script-review workflow checks for, with the reasoning behind each
one.
