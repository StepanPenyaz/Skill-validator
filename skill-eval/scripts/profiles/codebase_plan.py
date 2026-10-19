"""
The `codebase-plan` profile: skills that investigate a codebase and write an implementation plan, usually by
delegating to subagents (feature analysis, impact analysis, migration planning).

    verified_glob   *.md (one verified plan per input)
    sandbox         <skill>/evals/sandbox/codebase/  copied into the run as ./codebase
                    <skill>/evals/sandbox/agents/*.md copied into the run as .claude/agents/
    run             tools: Skill, Read, Glob, Grep, Agent, Write. The plan is read from plan.md, else the reply.
    score           0.55 x file recall + 0.20 x grounding + 0.25 x structure
                    (weights, layers and extensions are in config.yaml, profiles.codebase-plan)
"""

import re
import shutil
from pathlib import Path

from profiles import Profile as BaseProfile
from profiles.document import identifier_facts


# ---------- paths and layers ----------

def normalize(text, prefix):
    """Lowercase, drop backticks and the sandbox folder prefix so `codebase/a/b.cs` and `a/b.cs` match."""
    text = text.replace("`", "").replace("\\", "/").lower()
    return re.sub(rf"(?<![\w/.\-]){re.escape(prefix.lower())}", "", text) if prefix else text


def extract_paths(text, profile):
    """File paths (directory/name.ext, ext from profile['path_extensions']) in the order they appear, no duplicates."""
    exts = "|".join(re.escape(e) for e in profile["path_extensions"])
    pattern = re.compile(rf"(?<![\w/.\-])(?:\./)?((?:[\w.\-]+/)+[\w.\-]+\.(?:{exts}))(?![\w/])")
    seen = []
    for p in pattern.findall(normalize(text, profile.get("sandbox_prefix", "codebase/"))):
        if p not in seen:
            seen.append(p)
    return seen


def layers_of(paths, profile):
    return {name for name, prefix in profile["layers"].items() if any(p.startswith(prefix.lower()) for p in paths)}


def codebase_index(root):
    """(files, dirs): paths relative to the sandbox codebase, lowercase, with forward slashes."""
    root = Path(root)
    files, dirs = set(), set()
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix().lower()
        (files if p.is_file() else dirs).add(rel)
    return files, dirs


# ---------- components ----------

def file_recall(verified_text, produced_text, profile):
    """Share of the verified plan's file paths and backticked identifiers found in the produced plan."""
    prefix = profile.get("sandbox_prefix", "codebase/")
    v_paths = extract_paths(verified_text, profile)
    identifiers = {normalize(i, prefix) for i in identifier_facts(verified_text)} - set(v_paths)
    produced = normalize(produced_text, prefix)
    missing = []
    for fact in v_paths + sorted(identifiers):
        if not re.search(rf"(?<![\w]){re.escape(fact)}(?![\w])", produced):
            missing.append(fact)
    total = len(v_paths) + len(identifiers)
    return (1.0 if total == 0 else (total - len(missing)) / total), missing, total


def grounding(produced_paths, verified_paths, index, profile):
    """Share of the produced plan's paths that are real or plausible: the file exists in the codebase, is in the
    verified plan, or is a new file inside a real project folder (nearest existing ancestor deep enough).
    A plan that names no file at all scores 0: it is not grounded in anything."""
    if not produced_paths:
        return 0.0
    files, dirs = index if index else (set(), set())
    depth = int(profile.get("min_existing_depth", 2))
    known = set(verified_paths)

    def ok(path):
        if path in files or path in known:
            return True
        parts = path.split("/")[:-1]
        while parts and "/".join(parts) not in dirs:
            parts.pop()
        return len(parts) >= depth

    return sum(1 for p in produced_paths if ok(p)) / len(produced_paths)


def phase_headings(text):
    return len(re.findall(r"^#{1,6}\s*(?:\d+[.)]\s*)?phase\b", text, flags=re.I | re.M))


def jaccard(a, b):
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def structure(verified_text, produced_text, v_paths, p_paths, profile):
    """Mean of: phase headings present, same layers touched (a layer the feature does not need must stay
    untouched), and a phase count close to the verified plan's."""
    v_phases, p_phases = phase_headings(verified_text), phase_headings(produced_text)
    present = 1.0 if p_phases else 0.0
    ratio = 1.0 if v_phases == p_phases else (min(v_phases, p_phases) / max(v_phases, p_phases) if max(v_phases, p_phases) else 1.0)
    layers = jaccard(layers_of(v_paths, profile), layers_of(p_paths, profile))
    return (present + layers + ratio) / 3


def score_case(verified_text, produced_text, profile, index=None):
    w = profile["weights"]
    v_paths = extract_paths(verified_text, profile)
    n_facts = file_recall(verified_text, "", profile)[2]
    if produced_text is None:
        return {"similarity": 0.0, "file_recall": 0.0, "grounding": 0.0, "structure": 0.0,
                "missing": [], "n_facts": n_facts, "no_output": True}
    p_paths = extract_paths(produced_text, profile)
    recall, missing, total = file_recall(verified_text, produced_text, profile)
    ground = grounding(p_paths, v_paths, index, profile)
    struct = structure(verified_text, produced_text, v_paths, p_paths, profile)
    total_score = w["file_recall"] * recall + w["grounding"] * ground + w["structure"] * struct
    return {"similarity": total_score * 100, "file_recall": recall * 100, "grounding": ground * 100,
            "structure": struct * 100, "missing": missing, "n_facts": total, "no_output": False}


# ---------- the profile ----------

class Profile(BaseProfile):
    """Skills that investigate a sample codebase and write a plan. Needs evals/sandbox/ in the skill folder."""

    components = [("file_recall", "File recall"), ("grounding", "Grounding"), ("structure", "Structure")]
    codebase = None  # index of the sandbox codebase, set by check_applicable

    def _sandbox(self, skill_dir):
        return Path(skill_dir) / "evals" / "sandbox"

    def check_applicable(self, skill_dir):
        sandbox = self._sandbox(skill_dir)
        code, agents = sandbox / "codebase", sandbox / "agents"
        if not code.is_dir() or not any(p.is_file() for p in code.rglob("*")):
            return False, (f"no sample codebase in {code}. This profile needs evals/sandbox/codebase/ (the project the "
                           "skill analyses) and, when the skill delegates, evals/sandbox/agents/*.md. "
                           "See references/profiles.md.")
        text = (Path(skill_dir) / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        named = set(re.findall(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`", text))
        have = {p.stem for p in agents.glob("*.md")} if agents.is_dir() else set()
        wanted = {n for n in named if n.endswith(("investigator", "planner", "agent", "reviewer", "explorer"))}
        if wanted - have:
            return False, f"SKILL.md names agents with no definition in {agents}: {', '.join(sorted(wanted - have))}"
        self.codebase = codebase_index(code)
        return True, ""

    def prepare(self, workdir, skill_dir, case_path):
        sandbox = self._sandbox(skill_dir)
        shutil.copytree(sandbox / "codebase", Path(workdir) / "codebase")
        agents = sandbox / "agents"
        if agents.is_dir():
            shutil.copytree(agents, Path(workdir) / ".claude" / "agents")

    def collect(self, reply, workdir):
        plan = Path(workdir) / "plan.md"
        if plan.is_file() and plan.read_text(encoding="utf-8", errors="replace").strip():
            return plan.read_text(encoding="utf-8", errors="replace")
        return reply

    def score(self, verified, produced):
        return score_case(verified, produced, self.cfg, self.codebase)

    def report_intro(self):
        w = self.cfg["weights"]
        sentence = (f"Similarity = {w['file_recall']:.2f} x file recall + {w['grounding']:.2f} x grounding "
                    f"+ {w['structure']:.2f} x structure.")
        bullets = [
            "**File recall:** share of the verified plan's file paths and backticked identifiers that appear in the "
            "produced plan: did it find the places that have to change?",
            "**Grounding:** share of the file paths the produced plan names that exist in the sample codebase, are in "
            "the verified plan, or are new files inside a real project folder. Invented paths lower it.",
            "**Structure:** phase headings present, the same layers touched (a layer the feature does not need must "
            "stay untouched), and a phase count close to the verified plan's."]
        return sentence, bullets
