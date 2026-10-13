# Changelog

## [1.1.0]

- Output similarity: `scripts/compute_similarity.py` scores each produced output against its verified output (0 to 100%), per case and per model. Written to `step_reports/05_similarity.md`.
- Similarity is defined per kind of skill. Profiles live in `references/similarity_config.yaml`; the `document` profile is implemented. See `references/similarity-profiles.md`.
- The comparison step now ends with a `Verdict:` line (Equivalent, Minor gaps, Major gaps).
- `final_report.md` has a new section 8, Model recommendation: a table of similarity, verdict, tokens, time and cost, and the recommended model chosen by a fixed rule. The tolerance is `recommendation.tolerance_points` in `references/models_config.yaml`.
- The summary names the recommended model. Section 5 shows similarity per case.
- Rule change: the skill still gets no numeric score; similarity scores outputs only.

## [1.0.0]

- Evaluation flow: structure check, rubric review, runs on several models, final report.
- `/skill-static-review` command: structure check with no Claude session.
- Each Claude step runs in its own subagent with a clean context.
- Each model run reports measured tokens, time and cost in `run_on_<model>_report.md`.
- `final_report.md` has numbered sections. With two versions it adds V1/V2 columns and charts.
- Reports are Markdown only.
