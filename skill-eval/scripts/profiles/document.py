"""
The `document` profile: skills that turn a text task into a structured text result, written as one
Markdown file per input (tickets, specs, reports). This is the behaviour skill-eval had before profiles
existed, moved here unchanged.

    verified_glob   *.md
    run             the model's reply is the output (tools: Skill, Read, Glob, Grep)
    score           0.60 x fact recall + 0.25 x content overlap + 0.15 x structure
                    (weights, sections and units are in config.yaml, profiles.document)
"""

import re
from collections import Counter

from profiles import Profile as BaseProfile


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


def score_case(verified_text, produced_text, profile):
    w = profile["weights"]
    facts = extract_facts(verified_text, profile)
    n_facts = len(facts["numbers"]) + len(facts["identifiers"])
    if produced_text is None:  # no output: every component is 0 and the case is marked missing
        return {"similarity": 0.0, "fact_recall": 0.0, "content_overlap": 0.0, "structure": 0.0,
                "missing": [], "n_facts": n_facts, "no_output": True}
    recall, missing = fact_recall(facts, produced_text, profile)
    overlap = f1_overlap(verified_text, produced_text)
    structure = structure_score(verified_text, produced_text, profile)
    total = w["fact_recall"] * recall + w["content_overlap"] * overlap + w["structure"] * structure
    return {"similarity": total * 100, "fact_recall": recall * 100, "content_overlap": overlap * 100,
            "structure": structure * 100, "missing": missing, "n_facts": n_facts, "no_output": False}


class Profile(BaseProfile):
    """Structured text such as tickets, specs and reports: one Markdown output per input."""

    components = [("fact_recall", "Fact recall"), ("content_overlap", "Content overlap"), ("structure", "Structure")]

    def score(self, verified, produced):
        return score_case(verified, produced, self.cfg)

    def report_intro(self):
        w = self.cfg["weights"]
        sentence = (f"Similarity = {w['fact_recall']:.2f} x fact recall + {w['content_overlap']:.2f} x content overlap "
                    f"+ {w['structure']:.2f} x structure.")
        bullets = [
            "**Fact recall:** share of concrete facts of the verified output (numbers with their unit, backticked "
            "identifiers) that appear in the produced output.",
            "**Content overlap:** unigram + bigram F1 between the two texts.",
            "**Structure:** required sections present, and the number of numbered items close to the verified one."]
        return sentence, bullets
