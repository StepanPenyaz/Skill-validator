# Task fixtures: format and authoring methodology

`skill-eval` runs a target skill against a fixed set of task prompts (see
`SKILL.md` Workflow step 2). This file defines the format for that fixture
and how to author one.

## Why a fixed fixture, not ad hoc prompts

When comparing two *versions* of the same skill, the same task prompts
must run against both versions unchanged — otherwise any difference in
cost or judgment could just be different tasks, not the version change.
The task set is therefore stored as its own fixture, separate from either
skill directory (the skill directory is exactly what varies between an
old/new comparison; the task list is the constant). This mirrors
`skill-review`'s `diff_reviews.py`: it diffs two skill directories against
fixed check logic; `skill-eval` runs one fixed task file against two skill
directories.

## Format

```yaml
# skill-eval/tests/fixtures/tasks/<skill-name>.yaml
tasks:
  - id: happy-path-<short-name>
    prompt: "..."
    source: "SKILL.md description example"
  - id: targets-<version>-fix
    prompt: "..."
    source: "CHANGELOG <version>: <what it fixed>"
  - id: boundary-<short-name>
    prompt: "..."
    source: "When NOT to Use — should decline or hand off"
```

- `id`: short, kebab-case, unique within the file. Used to label rows and
  logs — pick something that reads as a label, not a UUID.
- `prompt`: the exact text sent to the target skill. This is what stays
  frozen across an old/new comparison — do not silently reword a prompt
  between runs being compared.
- `source`: where the prompt came from (see below). Not used
  programmatically; it's there so a reader can tell *why* this task is in
  the set without having to reverse-engineer it later.

## Where prompts come from

Pull tasks from these sources, in this priority order:

1. **The target skill's own `description` / "When to Use" section.**
   These already contain example invocation phrasings — that's what
   they're for. Use one close to verbatim for the happy-path task.
2. **Whatever actually changed, when comparing two versions.** Read the
   target skill's `CHANGELOG.md` entry for the version being compared
   against (or run `skill-review`'s
   `scripts/diff_reviews.py old_skill/ new_skill/` to see the findings
   delta directly), and write at least one task that specifically
   exercises that change. A task that doesn't touch the changed code path
   can't show whether the change helped — this is the task most likely to
   make the comparison actually meaningful, not just generic noise.
3. **The target skill's "When NOT to Use" section.** One boundary-case
   task — checks the skill still declines or hands off appropriately
   rather than over-triggering.
4. **A real past transcript, if one exists.** More realistic than
   anything hand-written; use it when available instead of inventing an
   equivalent.

## How many tasks

3-5 tasks as a starting guideline: enough that a single run isn't the only
data point (LLM behavior and token counts have real run-to-run variance
even for the same prompt), small enough to keep `skill-eval`'s own cost
proportionate to the decision it's informing. Scale up only if the target
skill has enough distinct behaviors that fewer tasks would leave real
functionality unexercised.

## Authoring is manual, for now

Writing `tasks.yaml` is a manual step — a human (or Claude, on request)
reads the target skill and writes the file by hand, the same way
`skill-review`'s `bad-skill` fixture was hand-authored rather than
generated. An assisted or automated drafting step (e.g. `skill-eval`
proposing candidate tasks from a skill's description/changelog for a human
to approve) is explicitly out of scope until this manual version has
proven useful in practice — automating task selection before knowing
whether the resulting tasks are actually good ones would optimize the
wrong thing first.
