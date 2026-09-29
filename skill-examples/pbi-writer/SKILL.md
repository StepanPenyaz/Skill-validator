---
name: pbi-writer
description: Turns technical documentation (API specs, design docs, ADRs, migrations, NFRs, integration descriptions, UI specs) into a ready-to-use PBI with the fields Title, Description and AC (Acceptance Criteria). Use when the user asks to write a PBI, user story, backlog item or ticket from a technical document, specification or feature description, even if the word "PBI" was not mentioned.
metadata:
  version: "1.0.0"
---

# PBI Writer

Takes technical documentation and produces one PBI with three fields: **Title**, **Description**, **AC**. Goal: an engineer who has not read the document understands what needs to be done and how the work will be accepted.

## Process

1. **Read the whole document.** Identify: the goal/problem, affected components, concrete values (response codes, limits, deadlines, field names, formats), constraints, and anything explicitly excluded from scope (out of scope).
2. **Determine the scope of one PBI.** One document is, as a rule, one PBI. If the document describes several independently deliverable parts (for example, a backend and a separate UI feature), write a separate PBI for each and explain the split in one line at the end. Do not break it down into technical tasks (no PBI "write tests" or "create a table") unless the document itself requires separate delivery.
3. **Write the fields** following the rules below.
4. **Check yourself:** every number, code and name in the PBI is present in the document; no requirement is invented; nothing important from the document is lost.

## Fields

### Title
- Exactly **one sentence**, up to ~15 words, no trailing period and no prefixes like "PBI:" or a number.
- Format: action + object + (value or context). For example: "Add an order cancellation endpoint for the customer".
- Name the outcome, not the activity ("Implement" instead of "Investigate"/"Work on").

### Description
- 3-6 sentences or a short paragraph plus, if needed, a list. Structure:
  - **Context/problem:** why this is needed (from the document).
  - **What we are doing:** the essence of the change at the level of behavior and the key technical decisions recorded in the document.
  - **Out of scope:** one line, if the document explicitly excludes something.
- A user story formulation ("As a <role>, I want <...>, so that <...>") is acceptable if the document has a clear role; for purely technical tasks a direct description is better.
- Do not copy the document; give what is needed for understanding. Keep technical details that matter for implementation (field names, limits).

### AC (Acceptance Criteria)
- Numbered list, **5-10 items**, each verifiable by a single test (yes/no).
- Use **Given / When / Then** for behavior; for constraints and non-functional requirements a direct statement with a measurable value is enough.
- Be sure to cover: the main scenario, error and edge cases from the document, non-functional requirements (performance, security, logging) if they are present.
- Use **concrete values from the document**, without words like "fast", "correct", "reasonable". If the document gives no values but a criterion is needed, do not invent a number: include the criterion and mark it `[clarify: ...]`.
- One criterion = one condition. Do not glue several checks together with "and".

## Gaps and contradictions
If the document is incomplete or contradictory, do not guess. After the PBI add an **Open questions** block (1-4 items) only if such questions really exist. If there are none, do not output the block.

## Language
Write in the language of the document; if the document's language is mixed or unclear, use the language of the user's request. Do not translate technical terms, field names, endpoints and codes.

## Output format

```
### Title
<one sentence>

### Description
<text>

### AC
1. ...
2. ...

### Open questions   (only if there are any)
- ...
```
