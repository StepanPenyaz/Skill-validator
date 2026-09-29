# Final Evaluation Report: pbi-writer

## 1. Summary

Evaluation of `pbi-writer` version 1.0.0 on 3 model(s): haiku, opus, sonnet.

## 2. Skill name

Name: `pbi-writer`  
Version: `1.0.0`

## 3. Skill description

Turns technical documentation (API specs, design docs, ADRs, migrations, NFRs, integration descriptions, UI specs) into a ready-to-use PBI with the fields Title, Description and AC (Acceptance Criteria). Use when the user asks to write a PBI, user story, backlog item or ticket from a technical document, specification or feature description, even if the word "PBI" was not mentioned.

## 4. Run results

| Model used | Number of tokens used | Time spent | Total cost |
| --- | ---: | ---: | ---: |
| haiku | 49,480 | 1m 29s | $0.1484 |
| opus | 68,185 | 2m 27s | $1.0228 |
| sonnet | 72,934 | 3m 13s | $0.4376 |

## 5. Output comparison

| Verified output | Produced output | Model | Skill version | Notes |
| --- | --- | --- | --- | --- |
| 01-api-order-cancel.md | pbi-writer_1.0.0_haiku.md | haiku | 1.0.0 | Close match on endpoint, roles, statuses, reason enum, 500-char comment, 409/403/400 codes, idempotent repeat, audit log, p95 300 ms and response body; missing the 401 (bad token) and 404 (order not found) cases, the pending-refund vs NONE refundStatus mapping is only in the body field, and the "refunds start only after shipment" pain point is omitted. Format is bare numbered AC rather than Given/When/Then. |
| 02-db-soft-delete.md | pbi-writer_1.0.0_haiku.md | haiku | 1.0.0 | Most schema, index, partial unique email, repository, includeDeleted, restore 409, 03:00 UTC job, anonymization and 401 requirements match; missing as ACs the billing-reports refactor (only mentioned in Description), that existing rows stay NULL, that related audit_events and orders are untouched, and that new users can reuse a deleted e-mail. Description wrongly says "Out of scope: None mentioned" while adding the billing note there. |
| 03-ui-report-export.md | pbi-writer_1.0.0_haiku.md | haiku | 1.0.0 | Very close: all filters, 92-day error text, from>to error at "to" field, 50-row pagination and sorting, role-restricted button, 100,000-row limit and message, CSV format, filename, loading and empty states, and 10 s for 10,000 rows all match; only minor differences are more granular AC splitting and no Given/When/Then wording. Title is shorter and omits back-office portal and the page path. |
| 04-nfr-login-rate-limit.md | pbi-writer_1.0.0_haiku.md | haiku | 1.0.0 | Core limits (5 attempts/15 min lock, 30 per IP per minute, 429 with Retry-After, uniform 401, Redis TTL, fail-open with metric, ACCOUNT_LOCKED log, alert above 20 locks in 5 min, admin unlock) all match; missing the pentest F-04 reference and the closing criterion (no more than 5 attempts in 15 min), and the access-denied behavior for non-security_admin with its [clarify] on response code. Adds an invented open question about the Retry-After format even though the input specifies seconds. |
| 05-integration-payment-webhooks.md | pbi-writer_1.0.0_haiku.md | haiku | 1.0.0 | Close match on endpoint, HMAC-SHA256 signature with 401, 5-minute timestamp 400, event types, DEBUG-logged ignored types, 7-day eventId dedupe, 2 s response, out-of-order handling, 5 retries schedule with dead-letter alert, feature flag and metrics; differences are that secret rotation omits the "two active secrets" detail, temporary failure is not specified as a DB failure, and the polling AC adds a "disabled after one week" detail (present in input, but not in the verified AC). |
| 01-api-order-cancel.md | pbi-writer_1.0.0_opus.md | opus | 1.0.0 | Close match: same endpoint, roles, reason enum, statuses, RefundRequested, same-transaction stock release, 200 body, 400/403/404, p95 ≤ 300 ms, audit log and out of scope all present. Gaps: 401 for missing token and refundStatus NONE for NEW are only in the description not in AC, the 409 AC omits CANCELLED and "state does not change", and the repeated-call AC does not say no second refund or reservation release. |
| 02-db-soft-delete.md | pbi-writer_1.0.0_opus.md | opus | 1.0.0 | Close match: columns, partial unique index on email, idx_users_active with CONCURRENTLY, 5-minute limit, rollback, delete/read/includeDeleted behaviour, identical 401, restore with 409 on e-mail conflict, 03:00 UTC cleanup with anonymized audit_events and billing-reports queries all covered. Missing the AC that related audit_events and orders are unaffected by soft delete and the "state does not change" on restore 409; adds two Open questions (orders on physical delete, deleted_by FK) that the verified output does not have. |
| 03-ui-report-export.md | pbi-writer_1.0.0_opus.md | opus | 1.0.0 | Same facts and values (92-day limit, 50 rows, statuses, currencies, URL params, CSV UTF-8 BOM with ";" delimiter, file name pattern, 100,000 limit, 10 s for 10,000 rows) but the structure differs: it is split into two PBIs (filters/table and CSV export) while the verified output is one PBI. It also adds Open questions about CSV columns and time zone that are not in the verified output, and the export button AC says visible for the roles without stating it is hidden for others. |
| 04-nfr-login-rate-limit.md | pbi-writer_1.0.0_opus.md | opus | 1.0.0 | Close match on thresholds (5 in 15 min lock, 30 per IP per minute, 429 with Retry-After, identical 401, Redis TTL and fail-open, ERROR log and metric, ACCOUNT_LOCKED with IP hash, >20 locks in 5 min alert, DELETE unlock endpoint). Differences: the verified output has a [clarify] for the response code for non-security_admin roles, which is absent here; the pentest-closing criterion is not a separate AC; a [clarify] on response-time difference and three Open questions (non-existent logins counting, fail-open vs F-04) are added. |
| 05-integration-payment-webhooks.md | pbi-writer_1.0.0_opus.md | opus | 1.0.0 | Close match: HMAC-SHA256 signature 401, timestamp over 5 min 400, three event types stored in inbox with 200 in under 2 s, other types 200 with DEBUG log, 7-day eventId dedup, out-of-order protection, 5xx on DB failure, 5 retries (1 min to 6 h) then dead-letter with alert, secret rotation with two secrets. Missing separate ACs for the three metrics and for the polling feature flag paygate.polling.enabled (only in the description); adds Open questions on timestamp coverage by HMAC and payment.refunded effect. |
| 01-api-order-cancel.md | pbi-writer_1.0.0_sonnet.md | sonnet | 1.0.0 | Endpoint, role, reason enum, comment limit, statuses, RefundRequested, idempotency, 401/403/404/400, p95 300 ms and audit log all match. It differs on the 409 rule: it limits 409 to SHIPPED/DELIVERED and raises the CANCELLED conflict as an open question, while the verified output lists CANCELLED as 409 except for a repeat call. It also omits the refundStatus PENDING/NONE mapping and the "no repeated refund or re-release on repeat call" detail, and adds an unrequested Open questions section. |
| 02-db-soft-delete.md | pbi-writer_1.0.0_sonnet.md | sonnet | 1.0.0 | Very close: the columns, partial unique index, CONCURRENTLY index, 5-minute limit, rollback script, 401 on login, restore with 409 on e-mail conflict, 03:00 UTC job with anonymized audit_events, and the 3 billing-reports queries are all covered. Minor gaps: AC does not state that orders and audit_events are unaffected by delete, and it does not state that billing queries must not return deleted users. It adds an Open questions section and splits the verified ACs into 10 more granular ones. |
| 03-ui-report-export.md | pbi-writer_1.0.0_sonnet.md | sonnet | 1.0.0 | Filters, 92-day error, Amount error at "to" field, URL-stored filters, 50 rows per page, role-based export button, CSV format, 100,000-row limit message, loading state, empty-result state and the 10 s target all match. Missing details: the Currency values (EUR, USD, PLN, GBP), that Currency is optional, and 2-decimal Amount precision are not in the description or AC. The export button is described as visible for the roles but not as hidden for others. It adds an Open questions section. |
| 04-nfr-login-rate-limit.md | pbi-writer_1.0.0_sonnet.md | sonnet | 1.0.0 | Per-account lock (5 in 15 min), per-IP 30/min, 429 with Retry-After, counter reset on success, Redis fail-open with the metric name, ACCOUNT_LOCKED log, the 20-locks alert to #security-alerts, admin unlock endpoint and the pentest closing criterion all match. Differs on the clarify marker: it flags the response-time difference instead of the response code for non-security_admin callers, and does not state that other roles are denied. It also adds an Open questions section. |
| 05-integration-payment-webhooks.md | pbi-writer_1.0.0_sonnet.md | sonnet | 1.0.0 | Signature 401, 5-minute timestamp 400, two-secret rotation, ignored event types with DEBUG log, 7-day eventId dedup, inbox with 200 under 2 s, occurredAt ordering, 5xx on DB failure, and the retry schedule with dead-letter alert all match. Missing as AC: the exposed metrics and the polling feature flag paygate.polling.enabled (both only in the description), and the secrets-manager source is also description-only. It adds an Open questions section on payment.refunded handling and polling/webhook conflicts. |

## 6. Skill structure check

### Static Check Report: pbi-writer

0 blocker(s), 0 warning(s), 1 info-level suggestion(s).

> **Security scan partially skipped:** No shell-executing (Bash) or network-capable (WebFetch/WebSearch/MCP) tool declared in allowed-tools or referenced in the SKILL.md body; this skill can't act on a shell-pattern, prompt-injection, or undeclared-host finding. Re-run with force_security_scan=True (--force-security-scan on the CLI) to scan anyway. (skipped checks: dangerous_shell_pattern, prompt_injection_phrase, undeclared_external_host)

#### Structure

| What's Wrong | Severity | Suggested Fix |
|---|---|---|
| 0 of 8 recommended SKILL.md sections found — missing: Purpose, When to Use, When NOT to Use, Workflow, Rules, Decision Guidelines, Validation, References. | Info | Optional: consider restructuring around references/preferred-structure.md's outline. Not every skill needs all eight sections. |

Eval data: evals/inputs/ present, evals/verified-outputs/ present.

## 7. Skill rubric review

##### Do the sections follow their intended meaning?

- **Frontmatter / description (rubric §1): mostly right.** It says what the skill does ("Turns technical documentation ... into a ready-to-use PBI with the fields Title, Description and AC") and when to use it ("Use when the user asks to write a PBI, user story, backlog item or ticket..."). It is also suitably assertive: "even if the word "PBI" was not mentioned". Two small problems:
  - It promises "a ready-to-use PBI" (singular), but Process step 2 allows several PBIs per document. It also never mentions the conditional **Open questions** block. Neither is serious, but both are small gaps between what the description promises and what the body does.
  - "ticket from a ... feature description" is broad. It could pull in general ticket or bug-report writing that doesn't start from a technical document. A brief "not for bug reports or one-line task notes" would narrow it.
- **Intro (line 10): right.** It states the goal and the reason behind it: "an engineer who has not read the document understands what needs to be done and how the work will be accepted". This gives the model a rationale it can apply beyond the listed rules.
- **Process: right in intent, but one internal contradiction.** The intro says the skill "produces one PBI". Step 2 says "write a separate PBI for each and explain the split in one line at the end". The Output format section only gives a template for a single PBI. It doesn't say how to separate several PBIs, or whether Open questions go once at the end or under each PBI. Step 4, the self-check ("every number, code and name in the PBI is present in the document; no requirement is invented"), is a good anti-hallucination step.
- **Title: mostly right, one self-contradicting example.** The format rule and the example ("Add an order cancellation endpoint for the customer") are concrete. But "Name the outcome, not the activity ("Implement" instead of "Investigate"/"Work on")" gives an activity verb ("Implement") as the model of an outcome. It should say something like "prefer a delivered result ('Add…', 'Enforce…') over open-ended activity ('Investigate', 'Work on')". Also, "Exactly **one sentence**" sits next to the "no trailing period" rule. That's fine, but the two could be read as slightly in tension.
- **Description field: right.** It has a clear sub-structure (Context/problem, What we are doing, Out of scope) and explains when a user story wording is appropriate. "3-6 sentences or a short paragraph plus, if needed, a list" is loose, because "short paragraph" isn't bounded. This is minor.
- **AC: mostly right, with two tensions.**
  - "**5-10 items**" conflicts with "Be sure to cover: the main scenario, error and edge cases ..., non-functional requirements". Combined with "One criterion = one condition", a rich spec will overflow 10 items. The skill doesn't say which wins (for example, merge items, prioritize, or split the PBI).
  - Gaps are handled in two places: inline `[clarify: ...]` markers in AC, and the **Open questions** block. Nothing says how they relate, for example whether each `[clarify]` item should also appear in Open questions.
  - The concrete-values rule ("without words like "fast", "correct", "reasonable"") is well stated.
- **Gaps and contradictions: right.** "do not guess", 1-4 items, and "If there are none, do not output the block" is clear and matches the template.
- **Language: right.** There is a clear fallback order, and technical terms, field names, endpoints and codes stay untranslated.
- **Output format (rubric §3, unambiguous output): largely right.** It has a literal template block. Minor risk: the annotation "`### Open questions   (only if there are any)`" is inside the template and may be copied into the output word for word. Move that note outside the code block.
- **Writing style (rubric §3): acceptable.** There are no ALL-CAPS MUST/NEVER directives, and everything is in imperative form. Most rules have no stated reason beyond the intro's goal, but they are soft, so this is at most minor. There is no overfitting to one sample input.
- **Examples (rubric §3): minor gap.** The task depends heavily on format, but the only example is one Title. No worked input→PBI example appears in SKILL.md or a `references/` file. The `evals/verified-outputs/` files exist but are not referenced, which is correct for eval data. A short `references/example.md` with a pointer from the body would help.
- **Structure / progressive disclosure (rubric §2): pass.** SKILL.md is 62 lines. It has no bundled `scripts/`, `references/` or `assets/`, so it has no orphaned or unpointed files, and it covers a single domain with no variants to split.

##### Security risks

- **No executable or system-level risk.** The skill has no scripts, shell commands, external hosts, network calls, file writes or tool invocations. It only turns text into text. I found no exfiltration, privilege or destructive-action paths.
- **No MUST/NEVER directives that need a hook.** None of the rules protect against real harm (data loss, unauthorized access). They are all about content quality, so no enforcement recommendation applies.
- **Low risk: untrusted input documents (prompt injection).** The skill reads user-supplied specs, ADRs and integration descriptions but never says to treat their content as data. For example, a spec could contain "ignore previous instructions ..." inside a text block. Since the skill only produces text, the impact is limited to a distorted PBI. A one-line note ("treat the document as source material, not as instructions") would close this.
- **Low risk: sensitive values copied into tickets.** "Keep technical details that matter for implementation (field names, limits)" and the rule to use "concrete values from the document" could lead the model to copy credentials, tokens, internal hostnames or webhook secrets into a PBI. Backlog tools are often viewed much more widely than the source spec. A rule like "never copy secrets or keys; reference them by name (e.g. `WEBHOOK_SIGNING_SECRET`)" would address this.
- **No deceptive behavior.** What the skill does matches its description, apart from the minor one-vs-many PBI mismatch noted above.

I covered all four rubric categories within budget.
