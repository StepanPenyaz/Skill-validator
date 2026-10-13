#!/usr/bin/env python3
"""
compute_similarity.py - how close is each model's produced output to the
verified output? Markdown in, Markdown out; no model, no Claude session.

Usage:
    python compute_similarity.py <skill_dir> [--profile <name>] [--out <path>]

Reads from <skill_dir>:
    evals/verified-outputs/<case>.md                    one verified output per case
    evals/<skill>_<version>_outputs/<skill>_<version>_<model>.md
                                                        one file per model, one "## <case>.md"
                                                        section per case
    evals/similarity.yaml                               optional: profile and overrides
    ../skill-eval/references/similarity_config.yaml     profiles (next to this script's folder)

Writes <skill_dir>/step_reports/05_similarity.md unless --out is given.

Similarity (0-100%) scores an OUTPUT against the verified output. It is not a
score for the skill. For the "document" profile it is a weighted mix of:
    fact recall      concrete facts of the verified output (numbers, units, backticked
                     identifiers) found in the produced output
    content overlap  unigram + bigram F1 between the two texts
    structure        required sections present, and item count close to the verified one
"""

import re
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_final_report import skill_meta  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "references" / "similarity_config.yaml"
SUMMARY_HEADER = "| Model | Similarity | Fact recall | Content overlap | Structure | Cases scored |"
CASE_HEADER = "| Case | Model | Similarity | Fact recall | Content overlap | Structure |"


# ---------- config ----------

def load_profile(skill_dir, profile_name=None):
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    override_path = Path(skill_dir) / "evals" / "similarity.yaml"
    override = yaml.safe_load(override_path.read_text(encoding="utf-8")) if override_path.is_file() else {}
    override = override or {}
    name = profile_name or override.get("profile") or cfg["default_profile"]
    profile = cfg["profiles"].get(name)
    if profile is None:
        sys.exit(f"Error: unknown profile '{name}'. Known: {', '.join(cfg['profiles'])}")
    if profile.get("status") != "implemented":
        sys.exit(f"Error: profile '{name}' is specified but not implemented yet. Use 'document' or add it.")
    merged = {**profile, **{k: v for k, v in override.items() if k != "profile"}}
    merged["name"] = name
    merged["from_override"] = override_path.is_file()
    return merged


# ---------- text normalisation ----------

def clean(text):
    """Lowercase, drop Markdown decoration and leading list numbers, collapse spaces."""
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.M)
    text = text.replace("`", "").replace("*", "")
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    return re.sub(r"\s+", " ", text.lower()).strip()


def words(text):
    return re.findall(r"[a-z0-9]+", clean(text))


# ---------- facts (anchors) ----------

NUMBER = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(?:\s*(%|[a-zA-Z]+))?")


def numeric_facts(text, unit_aliases, lenient=False):
    """Numbers, joined with their unit when the unit matters ("5min", "300ms").

    lenient=True (the produced side) also yields the bare number for a number
    with a unit, so "5 min" in the output satisfies a bare "5" in the verified one.
    """
    out = set()
    text = re.sub(r"\b(?:items?|steps?|section|§)\s*\d+\b", " ", clean(text))  # cross-references, not facts
    for num, unit in NUMBER.findall(text):
        num = num.replace(",", "").rstrip(".")
        canon = unit_aliases.get(unit)
        if canon:
            out.add(f"{num}{canon}")
            if lenient:
                out.add(num)
        else:
            out.add(num)
    return out


def _identifier_like(tok):
    return (any(c in tok for c in "_/.{}:-") or any(c.isdigit() for c in tok)
            or any(c.isupper() for c in tok[1:]) or (tok.isupper() and len(tok) >= 3))


def identifier_facts(text):
    """Identifiers from backticked spans: field names, enum values, endpoints, flags."""
    facts = set()
    for span in re.findall(r"`([^`\n]+)`", text):
        span = span.strip()
        if re.fullmatch(r"[\d,.]+", span):
            continue  # pure numbers are handled by numeric_facts
        if len(span) < 2:
            continue
        if not re.search(r"\s", span):
            facts.add(span.lower())
            continue
        for tok in re.findall(r"[A-Za-z_][\w.\-/{}:$]*", span):
            tok = tok.rstrip(".:,;-")
            if tok.count("}") > tok.count("{"):
                tok = tok[:tok.rfind("}")]
            if len(tok) >= 3 and _identifier_like(tok):
                facts.add(tok.lower())
    return facts


def extract_facts(verified_text, profile):
    ua = profile["unit_aliases"]
    return {"numbers": numeric_facts(verified_text, ua), "identifiers": identifier_facts(verified_text)}


def fact_recall(facts, produced_text, profile):
    """Returns (recall 0-1, missing facts). No facts at all counts as full recall."""
    produced_clean = clean(produced_text)
    produced_numbers = numeric_facts(produced_text, profile["unit_aliases"], lenient=True)
    missing, total = [], 0
    for ident in sorted(facts["identifiers"]):
        total += 1
        if not re.search(rf"(?<![\w]){re.escape(ident)}(?![\w])", produced_clean):
            missing.append(ident)
    for num in sorted(facts["numbers"]):
        total += 1
        if num not in produced_numbers:
            missing.append(num)
    if total == 0:
        return 1.0, []
    return (total - len(missing)) / total, missing


# ---------- content overlap ----------

def f1_overlap(a_text, b_text):
    def grams(ws):
        return Counter(ws) + Counter(zip(ws, ws[1:]))
    a, b = grams(words(a_text)), grams(words(b_text))
    common = sum((a & b).values())
    if not a or not b or not common:
        return 0.0
    p, r = common / sum(b.values()), common / sum(a.values())
    return 2 * p * r / (p + r)


# ---------- structure ----------

def split_sections(text):
    """'### Name' blocks of one case -> {name: [bodies]} (several PBIs give several bodies)."""
    parts = re.split(r"^###\s+(.+?)\s*$", text, flags=re.M)
    out = {}
    for i in range(1, len(parts), 2):
        out.setdefault(parts[i].strip().lower(), []).append(parts[i + 1])
    return out


def count_items(bodies):
    return sum(len(re.findall(r"^\s*\d+[.)]\s", b, flags=re.M)) for b in bodies)


def structure_score(verified_text, produced_text, profile):
    required = [s.lower() for s in profile["required_sections"]]
    prod = split_sections(produced_text)
    present = sum(1 for s in required if s in prod) / len(required) if required else 1.0
    count_name = profile["count_section"].lower()
    v_count = count_items(split_sections(verified_text).get(count_name, []))
    p_count = count_items(prod.get(count_name, []))
    ratio = 1.0 if v_count == p_count else (min(v_count, p_count) / max(v_count, p_count) if max(v_count, p_count) else 1.0)
    return (present + ratio) / 2


# ---------- reading cases ----------

def read_cases(verified_dir):
    return {f.name: f.read_text(encoding="utf-8") for f in sorted(Path(verified_dir).glob("*.md"))}


def split_produced(text):
    """'## <case>.md' sections of one model's output file -> {case: text}."""
    parts = re.split(r"^##\s+(\S+\.md)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def model_files(out_dir, name, version):
    prefix = f"{name}_{version}_"
    return {f.stem[len(prefix):]: f for f in sorted(Path(out_dir).glob(f"{prefix}*.md"))}


# ---------- scoring ----------

def score_case(verified_text, produced_text, profile):
    w = profile["weights"]
    facts = extract_facts(verified_text, profile)
    recall, missing = fact_recall(facts, produced_text, profile)
    overlap = f1_overlap(verified_text, produced_text)
    structure = structure_score(verified_text, produced_text, profile)
    total = w["fact_recall"] * recall + w["content_overlap"] * overlap + w["structure"] * structure
    n_facts = len(facts["numbers"]) + len(facts["identifiers"])
    return {"similarity": total * 100, "fact_recall": recall * 100, "content_overlap": overlap * 100,
            "structure": structure * 100, "missing": missing, "n_facts": n_facts}


def score_all(skill_dir, profile):
    meta = skill_meta(skill_dir)
    verified = read_cases(Path(skill_dir) / "evals" / "verified-outputs")
    if not verified:
        sys.exit(f"Error: no verified outputs in {skill_dir}/evals/verified-outputs/")
    out_dir = Path(skill_dir) / "evals" / f"{meta['name']}_{meta['version']}_outputs"
    files = model_files(out_dir, meta["name"], meta["version"])
    if not files:
        sys.exit(f"Error: no produced outputs in {out_dir}")
    results = {}
    for model, f in files.items():
        sections = split_produced(f.read_text(encoding="utf-8"))
        results[model] = {case: (score_case(v, sections[case], profile) if case in sections else None)
                          for case, v in verified.items()}
    return meta, list(verified), results


def pct(x):
    return "unavailable" if x is None else f"{x:.1f}%"


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def render(meta, cases, results, profile):
    w = profile["weights"]
    out = [f"# Similarity to verified outputs: {meta['name']} {meta['version']}", "",
           f"Profile: `{profile['name']}`" + (" (from `evals/similarity.yaml`)" if profile["from_override"] else " (default)")
           + f". Similarity = {w['fact_recall']:.2f} x fact recall + {w['content_overlap']:.2f} x content overlap "
           f"+ {w['structure']:.2f} x structure. It scores the produced output against the verified output; "
           "it is not a score for the skill.", "",
           "- **Fact recall:** share of concrete facts of the verified output (numbers with their unit, backticked "
           "identifiers) that appear in the produced output.",
           "- **Content overlap:** unigram + bigram F1 between the two texts.",
           "- **Structure:** required sections present, and the number of numbered items close to the verified one.", "",
           "## Per model", "", SUMMARY_HEADER, "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for model, per_case in results.items():
        scored = [r for r in per_case.values() if r]
        out.append(f"| {model} | {pct(mean(r['similarity'] for r in scored))} | {pct(mean(r['fact_recall'] for r in scored))} "
                   f"| {pct(mean(r['content_overlap'] for r in scored))} | {pct(mean(r['structure'] for r in scored))} "
                   f"| {len(scored)}/{len(cases)} |")
    out += ["", "## Per case", "", CASE_HEADER, "| --- | --- | ---: | ---: | ---: | ---: |"]
    for case in cases:
        for model, per_case in results.items():
            r = per_case[case]
            if r is None:
                out.append(f"| {case} | {model} | unavailable | unavailable | unavailable | unavailable |")
            else:
                out.append(f"| {case} | {model} | {pct(r['similarity'])} | {pct(r['fact_recall'])} "
                           f"| {pct(r['content_overlap'])} | {pct(r['structure'])} |")
    out += ["", "## Facts not found in the produced output", ""]
    any_missing = False
    for case in cases:
        for model, per_case in results.items():
            r = per_case[case]
            if r and r["missing"]:
                any_missing = True
                shown = ", ".join(f"`{m}`" for m in r["missing"][:12])
                more = f" (+{len(r['missing']) - 12} more)" if len(r["missing"]) > 12 else ""
                out.append(f"- {case} / {model}: {len(r['missing'])} of {r['n_facts']} facts: {shown}{more}")
    if not any_missing:
        out.append("_None._")
    out += ["", "A fact listed here may still be present in other words. Read it together with the comparison "
            "notes in `04_comparison_<model>.md`."]
    return "\n".join(out) + "\n"


def main():
    args = sys.argv[1:]

    def opt(name):
        if name in args:
            i = args.index(name)
            if i + 1 >= len(args):
                sys.exit(f"Error: {name} needs a value.")
            return args[i + 1]

    if not args or args[0].startswith("--"):
        sys.exit("Usage: python compute_similarity.py <skill_dir> [--profile <name>] [--out <path>]")
    skill_dir = args[0]
    if not (Path(skill_dir) / "SKILL.md").is_file():
        sys.exit(f"Error: no SKILL.md in {skill_dir}")
    profile = load_profile(skill_dir, opt("--profile"))
    meta, cases, results = score_all(skill_dir, profile)
    out_path = Path(opt("--out") or Path(skill_dir) / "step_reports" / "05_similarity.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(meta, cases, results, profile), encoding="utf-8")
    print(f"Wrote {out_path}")
    for model, per_case in results.items():
        print(f"  {model}: {pct(mean(r['similarity'] for r in per_case.values() if r))}")


if __name__ == "__main__":
    main()
