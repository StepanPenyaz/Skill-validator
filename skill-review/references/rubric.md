# Skill Review Rubric

This rubric is for judgment calls that a script can't make reliably — it
complements `structural_check.py`, which handles the objectively-checkable
facts (frontmatter validity, line counts, orphaned files, portability).

Score each category **Pass / Minor / Major / Blocker**:
- **Blocker** — will actively cause the skill to fail, mislead, or misbehave.
- **Major** — will noticeably hurt real-world performance or triggering.
- **Minor** — polish; worth fixing but not urgent.
- **Pass** — no issue.

For every Minor/Major/Blocker finding, write a concrete rewrite, not just a
diagnosis. "This is too vague" is not useful on its own; show the fixed text.

---

## 1. Description & Triggering Quality

The `description` field is the *only* thing Claude sees before deciding
whether to consult the skill. Judge it as a triggering mechanism, not a
summary.

- **Covers WHAT and WHEN.** It must state both what the skill does and the
  specific contexts/phrases that should trigger it. A description that only
  says what the skill does ("Formats Excel spreadsheets") will under-trigger
  compared to one that also names contexts ("...use this whenever the user
  mentions a spreadsheet, workbook, .xlsx file, or wants data cleaned up,
  even if they don't say 'Excel' explicitly").
- **Appropriately pushy.** Claude currently tends to *under*-trigger skills.
  A good description leans assertive: "Make sure to use this whenever...",
  "Trigger even if they just say...". A flat, hedged description
  ("This skill can be used for...") is a Major finding.
- **Concrete, not generic.** Vague phrasing ("helps with documents") gives
  Claude nothing to pattern-match against a real user message. Compare
  against realistic user phrasing the skill should catch.
- **No over-promising.** The description shouldn't claim capabilities the
  body doesn't actually deliver — that's a Blocker (user-facing surprise).
- **Doesn't collide with adjacent skills.** If the description is so broad
  it would also claim tasks better handled elsewhere (or by Claude natively,
  for simple one-step tasks), flag as Major — this causes both over- and
  under-triggering.

## 2. Structure & Progressive Disclosure

Skills load in three tiers: metadata (always in context) → SKILL.md body
(in context once triggered) → bundled resources (loaded on demand). Judge
whether the skill respects this.

- **SKILL.md body stays lean.** Long SKILL.md bodies (flagged by the script
  at >500 lines) should push detail into `references/`, not stay inline.
  If the script flags this, check whether the excess is genuinely
  always-needed context or could be split out.
- **Bundled resources are pointed to, not just present.** Every file in
  `scripts/`, `references/`, `assets/` needs a clear inline pointer in the
  body telling Claude when to open it. (The script's orphan-file list is a
  *candidate* signal, not a verdict — a script invoked as `python -m
  scripts.foo` won't literally contain "foo.py" as a substring but may
  still be correctly referenced. Re-check each candidate against the actual
  body text before reporting it.)
- **Domain/variant organization.** If the skill covers multiple
  frameworks/domains (e.g. AWS vs GCP vs Azure), check whether it splits
  them into separate reference files selected by the main SKILL.md, rather
  than interleaving all variants inline.
- **Large reference files are navigable.** >300-line reference files need a
  table of contents (the script already checks for this mechanically —
  just carry the finding through).

## 3. Writing Style & Content Quality

- **Explains why, not just what.** Heavy use of unexplained ALL-CAPS
  MUST/NEVER/ALWAYS (see the script's `imperative_marker_counts`) is a
  yellow flag. Good skills explain the reasoning so the model can
  generalize past the letter of the rule. A skill that's mostly rigid
  directives with no rationale is a Major finding — rewrite at least the
  worst offenders to state the "why."
- **Principle of Lack of Surprise.** The skill's actual behavior shouldn't
  surprise a user who read its description. Skills that quietly do
  something beyond their stated scope, or that could facilitate malicious
  or deceptive use (exfiltration, unauthorized access, misleading output)
  are a Blocker — do not soften this finding.
- **Generalizes, not overfit.** Watch for instructions anchored tightly to
  one hypothetical example rather than the general case (e.g. hardcoded
  sample filenames, one narrow input format assumed to be the only one).
  This produces skills that work great on the author's test case and
  poorly elsewhere. Major finding if pervasive, Minor if isolated.
- **Imperative form.** Instructions should read as direct steps to follow,
  not passive description of what "the assistant might do."
- **Examples pattern used where it helps.** For format-sensitive or
  pattern-matching tasks (e.g. commit messages, output templates),
  concrete input→output examples meaningfully help; their total absence in
  a skill that would benefit from them is a Minor-to-Major finding
  depending on how format-sensitive the task is.
- **Output format is unambiguous.** If the skill produces a structured
  artifact (a report, a template, a fixed schema), the expected structure
  should be spelled out explicitly (e.g. a literal template block), not
  left to be inferred.

## 4. Safety & Security

- Flag anything that could compromise system security, exfiltrate data, or
  enable unauthorized access as a **Blocker**, regardless of how the skill
  frames its own purpose.
- Roleplay/persona skills are fine; skills designed to mislead the user
  about what they're actually doing are not.
