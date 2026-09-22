# csv-cleaner — improvement progress

Running log of the fix-and-rerun cycle for the `csv-cleaner` demo skill, one
`skill-review` finding at a time. Each entry links to the version snapshot
and, once a next version exists, the `diff_reviews.py` output between it and
its predecessor. See [`versions/README.md`](versions/README.md) for the
folder layout and how to diff any two versions yourself.

## v1 — baseline

**Verdict: `blocked`**

| Category | Score |
|---|---|
| Compliance | Pass |
| Safety | **Blocker** |
| Description & Triggering | Major |
| Structure & Progressive Disclosure | Minor |
| Writing Style & Content | Minor |

Findings: F1 undisclosed external call (Blocker), F2 thin description
(Major), F3 unsafe overwrite-without-backup (Major), F4 orphaned
`legacy_notes.md` (Minor), F5 two directives crammed on one line (Minor).

Full detail: [`versions/v1/reports/review.md`](versions/v1/reports/review.md).

---

*(next entry lands here once v2 is produced, together with the
`diff_reviews.py` diff against v1)*
