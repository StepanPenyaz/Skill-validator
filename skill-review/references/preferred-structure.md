# Preferred SKILL.md Structure

This is a recommended section outline for a `SKILL.md` body — a starting
template, not a requirement. `structural_check.py` reports which of these
sections it found (`metrics.preferred_structure_sections`) as a soft signal
only: a missing section is never a `compliance_errors` entry, since plenty of
valid skills don't need all eight (a skill with an obviously narrow scope may
not need a meaningful "When NOT to Use," for example).

Kept as its own file, separate from `rubric.md` and `schema.md`, so the
outline itself can be revised independently as conventions evolve.

```markdown
---
name: my-skill
description: ...
---

# Purpose

What this skill does.

# When to Use

When Claude should use this skill.

# When NOT to Use

When Claude should not use it.

# Workflow

1. Understand the task.
2. Inspect the relevant files.
3. Choose the appropriate approach.
4. Execute the changes.
5. Validate the result.

# Rules

## Rule 1
...

## Rule 2
...

# Decision Guidelines

If X → do A.

If Y → do B.

# Validation

Before finishing:
- Check X
- Check Y
- Run Z

# References

For detailed information:
- `references/architecture.md`
- `references/api.md`
```

## Notes on each section

- **Purpose** — one or two sentences on what the skill does. Keep it short;
  the frontmatter `description` already carries the triggering signal.
- **When to Use / When NOT to Use** — the triggering boundary in prose, more
  detailed than the frontmatter description can afford to be. "When NOT to
  Use" is especially useful for skills that are easy to over-trigger.
- **Workflow** — the step-by-step process, ordered as Claude should actually
  execute it.
- **Rules** — hard constraints, ideally each with a brief rationale (see
  `rubric.md`'s writing-style guidance on explaining *why*, not just
  asserting MUST/NEVER).
- **Decision Guidelines** — if/then judgment calls that don't fit neatly into
  the linear Workflow.
- **Validation** — a concrete checklist to run before considering the task
  done.
- **References** — pointers to `references/` files, each with a one-line cue
  for when to open it (this also keeps `orphaned_resource_files` clean).
