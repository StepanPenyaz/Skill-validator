# Static Check Report: pbi-writer

0 blocker(s), 0 warning(s), 1 info-level suggestion(s).

> **Security scan partially skipped:** No shell-executing (Bash) or network-capable (WebFetch/WebSearch/MCP) tool declared in allowed-tools or referenced in the SKILL.md body; this skill can't act on a shell-pattern, prompt-injection, or undeclared-host finding. Re-run with force_security_scan=True (--force-security-scan on the CLI) to scan anyway. (skipped checks: dangerous_shell_pattern, prompt_injection_phrase, undeclared_external_host)

## Structure

| What's Wrong | Severity | Suggested Fix |
|---|---|---|
| 0 of 8 recommended SKILL.md sections found — missing: Purpose, When to Use, When NOT to Use, Workflow, Rules, Decision Guidelines, Validation, References. | Info | Optional: consider restructuring around references/preferred-structure.md's outline. Not every skill needs all eight sections. |

Eval data: evals/inputs/ present, evals/verified-outputs/ present.
