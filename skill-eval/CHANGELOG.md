# Changelog

## [1.0.0]

- Evaluation flow: structure check, rubric review, runs on several models, final report.
- `/skill-static-review` command: structure check with no Claude session.
- Each Claude step runs in its own subagent with a clean context.
- Each model run reports measured tokens, time and cost in `run_on_<model>_report.md`.
- `final_report.md` has numbered sections. With two versions it adds V1/V2 columns and charts.
- Reports are Markdown only.
