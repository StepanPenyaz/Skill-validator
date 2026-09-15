# skill-eval end-to-end demo: evaluating skill-review

Real output from running `skill-eval`'s complete Workflow (issue #27) —
not a synthetic example. Target skill: `skill-review` itself. Task
fixture: `tests/fixtures/tasks/skill-review.yaml` (issue #21). Model list:
`references/models_config.yaml`'s default (`sonnet` only).

## Important correction to references/token-capture.md

`references/token-capture.md` (issue #23) concluded that no mechanism in
this environment exposes real per-subagent token usage, and designed
Workflow step 2 around a self-reported, labeled *estimate* instead
(`(prompt + response length) / 4`).

Running this demo for real surfaced that this conclusion was **incomplete**:
spawning the step-2 subagent through the top-level `Agent` tool directly
(as opposed to through a Workflow script's `agent()` wrapper, which is
what the original research spike used) returned real usage metadata
alongside the subagent's final report —
`subagent_tokens: 89012, tool_uses: 13, duration_ms: 123032` — with no
self-reporting or estimation needed at all. The blocker the spike found
(an `Agent`-tool subagent never exposes a `session_id` for a *separate*
introspection tool to query) is real, but doesn't apply here: the usage
data comes back attached to the `Agent` tool's own result, not from a
follow-up call to another tool.

**This means Workflow step 2 and `references/token-capture.md` are more
pessimistic than necessary and should be revisited** — real numbers may
be available for the actual design (one subagent per model, spawned by
whatever is orchestrating `skill-eval`), not just for a raw `Agent` tool
call made directly in a conversational turn like this demo. Flagging
rather than quietly "fixing" it here, since confirming exactly how this
generalizes (does it hold for every `Agent` invocation? does a Workflow's
`agent()` actually not surface it, or did the original spike simply not
check the call's own return value?) is its own piece of work.

The table below uses the **real, measured** numbers this run actually
returned — not the estimated-token design — with `tokens_estimated: false`
in the underlying data.

## The run

Stage 1a (`skill-review`'s gate mode against itself): 0 `compliance_errors`,
9 `structural_warnings` — all 9 confirmed, by hand, against the rubric's
"confirm before reporting" instruction, to be the scanner's own
self-referential false positives (its `DANGEROUS_SHELL_PATTERNS`/
`PROHIBITED_ACTION_PATTERNS` regex *definitions* matching their own source
in `structural_check.py`, plus one meta-documentation sentence in
`SKILL.md` that mentions "a MUST/NEVER line" as a descriptive example
rather than containing an actual directive) — not real issues. Passed,
proceeded to 1b.

Stage 1b (`skill-review`'s full review mode against itself, scored against
`references/rubric.md`): all four qualitative categories — description &
triggering, structure & progressive disclosure, writing style & content,
safety & security — genuinely scored **Pass**. Notable structural facts
backing that: 327-line body (well under the 500-line guideline), all 8
`preferred-structure.md` sections present, zero orphaned resources, and
exactly one `MUST`/`NEVER`-marked line in the entire `SKILL.md` (the same
meta-documentation false positive from stage 1a — not a real bare
directive). `overall_verdict: pass`. Passed, proceeded to step 2.

Step 2: spawned one `sonnet` subagent covering all three tasks from
`tests/fixtures/tasks/skill-review.yaml` in a single conversation, per
Workflow step 2's design. It read `skill-review/SKILL.md` itself and
followed it — including running `structural_check.py`/
`generate_static_report.py` via Bash for real, not describing what it
would do.

Step 3: judgment written from the subagent's actual transcript (below).

Step 4: rendered with `scripts/render_report.py`.

## Result

> **Gate check** (via skill-review) — passed, evaluation proceeded:
> - Stage 1a (deterministic): 9 structural warning(s), not blocking.
> - Stage 1b (qualitative): `overall_verdict` = `pass`, not blocking.

| Model Used | Number of Tokens | Time Spent | Claude's Judgment |
|---|---:|---:|---|
| sonnet | 89,012 | 2m 3s | • Correctly triaged task interpretation per task rather than applying one mode to everything: ran the full qualitative review for task 1's casual "what's wrong with my skill" phrasing, but restricted to gate-mode only for task 2's explicit "quick gate-mode check" phrasing, matching skill-review's own Decision Guidelines routing rule.<br>• In task 1, explicitly identified and dismissed `structural_check.py`'s own "Heavy unexplained MUST/NEVER usage" line as a false positive (it's the `bad-skill` fixture's meta-description of itself, not an actual directive) instead of reporting it as a real finding — direct evidence of following the rubric's "confirm before reporting" instruction rather than rubber-stamping every candidate.<br>• In task 2, quoted the exact `metrics.security_scan` JSON object (`skipped`/`checks_skipped`/`reason`) and correctly distinguished it from `hardcoded_secret`/`prohibited_action_phrase` (never gated) — got the 1.6.0 cost-conditional-scan mechanism exactly right, not just a surface-level yes/no answer.<br>• In task 3, quoted skill-review's own "When NOT to Use" section nearly verbatim and pointed to `skill-creator` rather than fabricating a runtime-performance claim — correctly declined the out-of-scope boundary question instead of over-triggering. |

## Reproducing this

```bash
python3 skill-eval/scripts/render_report.py <input.json> --out skill-eval-eval.md
```

The `<input.json>` this run actually used, and the subagent's full raw
transcript (all three tasks in detail, not just the judgment summary
above), are recorded in this repository's PR history for the commit that
added this file — not duplicated here, to keep this file focused on the
result rather than the raw log.
