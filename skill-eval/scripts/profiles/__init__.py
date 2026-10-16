"""
Profiles: everything in skill-eval that depends on WHAT the skill under review works with.

The core of skill-eval (steps, repeats, stability, judges, reports, the model recommendation) knows
nothing about the kind of skill. A profile answers the five questions that do depend on it:

    verified_glob            which files in evals/verified-outputs/ are verified outputs (data)
    run_options()            the prompt and the tools a model run gets (run)
    collect(reply, workdir)  the produced output of one case, from the model's reply or the files in
                             the working directory (collection)
    score(verified, produced) how close the output is to the verified one: {"similarity": 0-100,
                             <one key per component>, "missing": [...], "n_facts": n, "no_output": bool}
                             (evaluation)
    check_applicable(skill_dir) (ok, note): can this profile judge this skill at all (applicability)

and describes itself for the report with `components` ([(key, column label)]) and `report_intro()`.

A profile lives in one module `profiles/<name>.py` (hyphens in the name become underscores) with a class
`Profile` that extends the base class below, and a section `profiles.<name>` in config.yaml with at least
`status: implemented`. `status: planned` entries only reserve the name.

To add a profile follow references/profiles.md, including the self-test in tests/test_profiles.py:
every implemented profile must score its verified output as 100, a missing output as 0, and a clearly
broken output lower than the verified one.
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build_final_report import load_config  # noqa: E402


class Profile:
    """Base class and contract of a profile. Subclasses override what differs."""

    name = ""
    components = []  # [(key, label)] of the parts the similarity is made of

    def __init__(self, name, cfg):
        self.name = name
        self.cfg = cfg

    @property
    def verified_glob(self):
        return self.cfg.get("verified_glob", "*")

    def run_options(self):
        """{"prompt": ..., "allowed_tools": [...]} for the model runs."""
        return {"prompt": self.cfg["prompt"], "allowed_tools": list(self.cfg["allowed_tools"])}

    def check_applicable(self, skill_dir):
        """(ok, note). A profile that cannot judge the skill returns (False, reason) and the run stops."""
        return True, ""

    def collect(self, reply, workdir):
        """The produced output of one case. Default: the model's reply."""
        return reply

    def score(self, verified, produced):
        raise NotImplementedError

    def report_intro(self):
        """(sentence, [bullet lines]) that explain the similarity in 05_similarity.md."""
        return "", []


def get_profile(name=None):
    """The profile `name` (default: default_profile of config.yaml). Exits with a clear message when the
    profile is unknown or only planned."""
    cfg = load_config()
    profiles = cfg.get("profiles") or {}
    name = name or cfg.get("default_profile")
    section = profiles.get(name)
    if section is None:
        sys.exit(f"Error: unknown profile '{name}'. Known: {', '.join(profiles)}")
    if section.get("status") != "implemented":
        sys.exit(f"Error: profile '{name}' is planned, not implemented yet. See references/profiles.md.")
    module = importlib.import_module(f"profiles.{name.replace('-', '_')}")
    return module.Profile(name, section)
