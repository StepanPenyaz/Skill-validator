"""Trivial helper script, deliberately never mentioned by name in SKILL.md's
body — the one genuinely new issue this fixture introduces relative to
tests/fixtures/diff-old-skill/, which has no scripts/ directory at all."""


def normalize_filename(name):
    return name.strip().lower().replace(" ", "-")
