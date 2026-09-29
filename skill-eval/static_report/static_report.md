# Static Check Report: skill-eval

0 blocker(s), 3 warning(s), 1 info-level suggestion(s).

> **Security scan partially skipped:** No shell-executing (Bash) or network-capable (WebFetch/WebSearch/MCP) tool declared in allowed-tools or referenced in the SKILL.md body; this skill can't act on a shell-pattern, prompt-injection, or undeclared-host finding. Re-run with force_security_scan=True (--force-security-scan on the CLI) to scan anyway. (skipped checks: dangerous_shell_pattern, prompt_injection_phrase, undeclared_external_host)

## Structure

| What's Wrong | Severity | Suggested Fix |
|---|---|---|
| 7 of 8 recommended SKILL.md sections found — missing: Validation. | Info | Optional: consider restructuring around references/preferred-structure.md's outline. Not every skill needs all eight sections. |

## Security

| What's Wrong | Severity | Suggested Fix |
|---|---|---|
| `scripts\structural_check.py:93` — Phrase resembling a prohibited high-risk action: "enter the password" | Warning | Review context; remove it if it directs a prohibited action (entering credentials, permanent deletion, bypassing captchas, etc.). |
| `scripts\structural_check.py:156` — Phrase resembling a prohibited high-risk action: "permanently delete" | Warning | Review context; remove it if it directs a prohibited action (entering credentials, permanent deletion, bypassing captchas, etc.). |
| `scripts\structural_check.py:157` — Phrase resembling a prohibited high-risk action: "wire transfer" | Warning | Review context; remove it if it directs a prohibited action (entering credentials, permanent deletion, bypassing captchas, etc.). |
