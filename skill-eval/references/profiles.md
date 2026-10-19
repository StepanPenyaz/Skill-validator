# Profiles

A **profile** holds everything in `skill-eval` that depends on what the skill under review works with. The rest (steps, repeats, stability, judges, reports, the model recommendation) is the same for every skill.

## Contents

1. What a profile answers
2. The profiles
3. The `document` profile
4. Choosing a profile
5. Adding a profile
6. Limits

## 1. What a profile answers

| Question | Hook in `profiles/<name>.py` | `document` |
|---|---|---|
| Which files are verified outputs? | `verified_glob` | `*.md` |
| How is the model asked, with which tools? | `run_options()` | prompt and tools from `config.yaml` |
| Where does the output of a case come from? | `collect(reply, workdir)` | the model's reply |
| How close is the output to the verified one? | `score(verified, produced)` | facts, words, structure |
| What must the clean working directory hold before the run? | `prepare(workdir, skill_dir, case_path)` | nothing |
| Can the profile judge this skill at all? | `check_applicable(skill_dir)` | always |
| How is the score explained in the report? | `components`, `report_intro()` | three components |

`score` returns `{"similarity": 0-100, <one key per component>, "missing": [...], "n_facts": n, "no_output": bool}`. Similarity is a score of an output against its verified output, never of the skill.

A profile has two parts: the module `scripts/profiles/<name>.py` (hyphens in the name become underscores) with a class `Profile` that extends `profiles.Profile`, and the section `profiles.<name>` in `config.yaml` with its settings. `status: implemented` makes it usable; `status: planned` only reserves the name and stops the run with a clear message.

## 2. The profiles

| Profile | For skills that produce | Similarity | Status |
|---|---|---|---|
| `document` | Structured text: tickets, specs, reports, summaries with fixed sections | 0.60 fact recall + 0.25 content overlap + 0.15 structure | implemented |
| `codebase-plan` | An implementation plan written after investigating a sample codebase, usually through subagents | 0.55 file recall + 0.20 grounding + 0.25 structure | implemented |
| `structured-data` | JSON, YAML, CSV | Share of keys and values that match exactly | planned |
| `code` | Code and scripts | Share of checks that pass (a check command) | planned |
| `classification` | Labels and decisions | Exact-match accuracy over the cases | planned |

## 3. The `document` profile

- **Fact recall** is the share of concrete facts of the verified output that appear in the produced output. Facts are numbers (joined with their unit when the unit matters: `5 min` and `5 minutes` match, `5 min` and `5 attempts` do not) and identifiers written in backticks (field names, enum values, endpoints, flags). Case and Markdown decoration are ignored. A cross-reference such as "see item 5" is not a fact. This is the main component, because a missing limit or status code is the failure that matters most.
- **Content overlap** is the F1 of word unigrams and bigrams between the two texts. It guards against output that has the right facts but is off topic or padded. It is low for any rewording, so it carries a small weight.
- **Structure** is the mean of two shares: required sections present (`required_sections`), and the closeness of the number of numbered items in `count_section` (smaller count divided by larger). When a model splits one input into several documents, their sections and items are counted together.

Extra content (for example an "Open questions" block the verified output does not have) is not penalised by the number. It is for the comparison step to note, and the `Verdict:` line reflects it.

## 3a. The `codebase-plan` profile

For skills that look at a project and write a plan (feature analysis, impact analysis, migration planning), often by delegating to subagents. The skill is run against a **sandbox** that you supply in the skill's folder:

```
<skill>/evals/sandbox/
├── codebase/        the project to analyse; copied into the run as ./codebase
└── agents/*.md      definitions of the subagents the skill delegates to; copied as .claude/agents/
```

`check_applicable` refuses the skill when `codebase/` is missing or empty, or when `SKILL.md` names an agent (a backticked name ending in `-investigator`, `-planner`, `-agent`, `-reviewer` or `-explorer`) that has no file in `agents/`. The sandbox sits under `evals/`, so it is never part of the packaged skill, and the model never sees `evals/verified-outputs/`.

The model gets `Skill, Read, Glob, Grep, Agent, Write` (no `Bash`), is asked to save the plan to `plan.md` and reply with it. The plan is read from `plan.md`, or from the reply when the file is missing. The score has three parts:

- **File recall** is the share of the verified plan's file paths and backticked identifiers (endpoints, symbols) found in the produced plan: did it find the places that have to change? `codebase/a/b.cs` and `a/b.cs` are the same file.
- **Grounding** is the share of the produced plan's file paths that exist in the sandbox codebase, appear in the verified plan, or are new files inside a real project folder (`min_existing_depth`). Invented folders lower it. A plan that names no file scores 0.
- **Structure** is the mean of three shares: `Phase` headings present, the same layers touched as in the verified plan (`layers` in `config.yaml`: a layer the feature does not need must stay untouched), and a phase count close to the verified one.

Write verified plans so that every existing file is named in backticks with its path relative to `codebase`, and every new file is introduced as "New file". Name an endpoint or symbol in backticks only when the input fixes it, because a different but valid name would count as missing. Extra files and extra prose are not penalised by the number; the judges' `Verdict:` line covers them.

Limits: there are several valid plans for most features, so recall rewards finding the expected files, not choosing the same design. What the skill does in the SQL `todos` table or other tools that `claude -p` does not have is not measured. Whether the investigators really ran in parallel and the skill did not investigate itself shows in the transcripts (`.jsonl`) and the tool counts of the run report; it is not part of the score.

## 4. Choosing a profile

The profile used is `default_profile` in `config.yaml` (`document`), or the one given with `--profile <name>` to `run_skill.py` and `compute_similarity.py`. Use the same profile for both. The report names the profile. If a profile is planned or cannot judge the skill (`check_applicable`), the run stops with a message instead of producing a number that means nothing.

Pick the profile by what the skill produces, not by how it is written: if the verified outputs are Markdown documents with sections, `document`; if they are code that has to compile and pass tests, `code`.

## 5. Adding a profile

Work through these in order. The profile is ready only after step 5.

Use `prepare` when a case needs more than the input file in its working directory (a sample project, agent definitions), as `codebase-plan` does.

1. **Input and output.** What does the skill receive, and what does it produce: text in the reply, or files?
2. **Verified output.** What counts as the reference: a finished result, a set of tests, or criteria? Set `verified_glob`.
3. **Metric.** Which score, 0 to 100, fits? Prefer deterministic checks (compare fields, build, run tests). Use a judge (a subagent scoring against criteria) only when nothing deterministic fits, and say in the report that it is less reliable.
4. **Run needs.** The prompt, the tools (`allowed_tools`), a sandbox if the model must write files or run commands, and the setup of the environment. Override `collect` when the output is in files. Note the security risk of running commands.
5. **Self-test.** `tests/test_profiles.py` runs the same checks on every implemented profile: the verified output scores 100, a missing output scores 0, a clearly broken output scores lower. Add cases for known good and bad outputs of the new kind.
6. **Applicability.** Implement `check_applicable` so the profile refuses skills it cannot judge.
7. **Register.** Add `profiles.<name>` to `config.yaml` with `status: implemented`, and describe it in this file and in the CHANGELOG.

## 6. Limits

- The score is a proxy. For `document`, rephrasing a fact ("five attempts") is missed by fact recall. The report lists the facts not found, so a reader can check them against the comparison notes.
- Three to five cases are a small sample. Differences of a point or two between models are inside the noise.
- Weights are starting values and are not calibrated against human ratings. Change them in `config.yaml` if a skill's quality depends on something else.
- Runs read the output from the reply or, in a profile that overrides `collect`, from the working directory. Reports are Markdown either way.
