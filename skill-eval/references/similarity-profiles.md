# Similarity profiles

Step 4b of `skill-eval` gives each produced output a similarity to the verified output, from 0 to 100%. The number lets the final report compare models side by side. It scores the **output**, not the skill.

Plain text similarity is not enough for every skill. A reworded ticket can be perfect, and a one-character change in a JSON value can make a result useless. So similarity is defined per kind of skill, as a **profile** in `references/similarity_config.yaml`.

## Choosing a profile

Add `evals/similarity.yaml` to the skill under review:

```yaml
profile: document
```

Without the file, `document` is used and the report says so. Any key of the profile (`weights`, `required_sections`, `count_section`, `unit_aliases`) can be overridden in the same file.

## Profiles

| Profile | For skills that produce | Similarity | Status |
|---|---|---|---|
| `document` | Structured text: tickets, specs, reports, summaries with fixed sections | 0.60 fact recall + 0.25 content overlap + 0.15 structure | implemented |
| `structured-data` | JSON, YAML, CSV | Share of keys and values that match exactly | planned |
| `code` | Code and scripts | Share of checks that pass (a command in `evals/similarity.yaml`) | planned |
| `classification` | Labels and decisions | Exact-match accuracy over the cases | planned |

### `document`

- **Fact recall** is the share of concrete facts of the verified output that appear in the produced output. Facts are numbers (joined with their unit when the unit matters: `5 min` and `5 minutes` match, `5 min` and `5 attempts` do not) and identifiers written in backticks (field names, enum values, endpoints, flags). Case and Markdown decoration are ignored. A cross-reference such as "see item 5" is not a fact. This is the main component, because a missing limit or status code is the failure that matters most.
- **Content overlap** is the F1 of word unigrams and bigrams between the two texts. It guards against output that has the right facts but is off topic or padded. It is low for any rewording, so it carries a small weight.
- **Structure** is the mean of two shares: required sections present (`required_sections`), and the closeness of the number of numbered items in `count_section` (smaller count divided by larger). When a model splits one input into several documents, their sections and items are counted together.

Extra content (for example an "Open questions" block the verified output does not have) is not penalised by the number. It is for the comparison step to note, and the `Verdict:` line reflects it.

## Limits

- The score is a proxy. Rephrasing a fact ("five attempts") is missed by fact recall. The report lists the facts not found, so a reader can check them against the comparison notes.
- Three to five cases are a small sample. Differences of a point or two between models are inside the noise.
- Weights are starting values and are not calibrated against human ratings. Change them in the config if a skill's quality depends on something else.
- A profile that is "planned" stops the script with a clear message. Add its scoring function in `compute_similarity.py` and set `status: implemented`.
