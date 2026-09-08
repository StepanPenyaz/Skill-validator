# Review Output Schema

The review produces two files: `<skill-name>-review.json` (machine-readable)
and `<skill-name>-review.md` (human-readable). The JSON is the source of
truth; the markdown is generated from it.

```json
{
  "skill_name": "example-skill",
  "reviewed_at": "2026-09-08T00:00:00Z",
  "overall_verdict": "pass | pass_with_suggestions | needs_work | blocked",
  "category_scores": {
    "compliance": "pass | blocker",
    "structure_and_progressive_disclosure": "pass | minor | major | blocker",
    "description_and_triggering": "pass | minor | major | blocker",
    "writing_style_and_content": "pass | minor | major | blocker",
    "safety": "pass | blocker"
  },
  "metrics": {
    "skill_md_body_line_count": 482,
    "description_word_count": 49,
    "resource_file_count": 11,
    "imperative_marker_counts": {"MUST": 0, "NEVER": 1, "ALWAYS": 2}
  },
  "findings": [
    {
      "id": "F1",
      "category": "description_and_triggering",
      "severity": "major",
      "location": "frontmatter.description",
      "issue": "Description states what the skill does but gives no triggering context — no 'when to use' cues.",
      "current_text": "Formats Excel spreadsheets and cleans up data.",
      "suggested_rewrite": "Formats and cleans up Excel spreadsheets — fixing headers, removing blank rows, standardizing date/number formats. Use this whenever the user mentions a spreadsheet, workbook, .xlsx/.xls/.csv file, or wants tabular data cleaned, reformatted, or fixed, even if they don't say 'Excel' explicitly.",
      "why_it_matters": "The description is the only signal Claude sees before deciding to consult the skill; without an explicit when-clause it will under-trigger."
    }
  ],
  "orphaned_resource_files_confirmed": [],
  "summary": "One-paragraph plain-language summary of overall health and the highest-priority fix."
}
```

**Field notes:**
- `overall_verdict`: `blocked` if any category is `blocker`; `needs_work` if
  any category is `major`; `pass_with_suggestions` if only `minor` findings
  exist; `pass` if everything is clean.
- `findings[].severity`: `minor | major | blocker` (matches rubric.md scale;
  "pass" findings aren't listed individually).
- `findings[].suggested_rewrite`: required for every finding except pure
  structural/compliance facts where the fix is mechanical (e.g. "move file
  X to references/") — for those, `suggested_rewrite` can describe the
  mechanical fix instead of prose.
- `orphaned_resource_files_confirmed`: the subset of the script's raw
  orphan-file candidates that you verified are actually unreferenced,
  after checking for indirect references (e.g. `python -m scripts.foo`).
