#!/usr/bin/env python3
"""
package_skill.py — shared packaging tool for every skill in this repo.

Zips a skill directory into a distributable `<name>.skill` bundle, stripping
dev-only content (tests/fixtures, VCS metadata, caches) so packaging never
ships more than one SKILL.md. Reused across skills in this solution instead
of each one vendoring its own copy.

Usage:
    python package_skill.py <skill_directory> [output_dir]
"""

import json
import re
import sys
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print(json.dumps({"fatal_error": "PyYAML not installed. Run: pip install pyyaml"}))
    sys.exit(1)

# Kept in sync with skill-review/scripts/structural_check.py's PACKAGING_EXCLUDE_DIRS.
EXCLUDE_DIRS = {"tests", ".git", "__pycache__", "dist", "node_modules", ".pytest_cache"}
EXCLUDE_FILE_SUFFIXES = {".pyc"}
EXCLUDE_FILENAMES = {".DS_Store"}


def fail(msg):
    print(json.dumps({"fatal_error": msg}))
    sys.exit(1)


def read_skill_name(skill_md_path):
    content = skill_md_path.read_text(errors="ignore")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        fail(f"{skill_md_path} has no valid YAML frontmatter.")
    fm = yaml.safe_load(match.group(1))
    name = (fm or {}).get("name")
    if not name:
        fail(f"{skill_md_path} frontmatter has no 'name'.")
    return name


def should_include(rel_path):
    parts = rel_path.parts
    if any(part in EXCLUDE_DIRS for part in parts):
        return False
    if rel_path.name in EXCLUDE_FILENAMES:
        return False
    if rel_path.suffix in EXCLUDE_FILE_SUFFIXES:
        return False
    if rel_path.suffix == ".skill":
        return False
    return True


def main():
    if len(sys.argv) not in (2, 3):
        fail("Usage: python package_skill.py <skill_directory> [output_dir]")

    skill_path = Path(sys.argv[1]).resolve()
    if not skill_path.is_dir():
        fail(f"Not a directory: {skill_path}")

    skill_md_path = skill_path / "SKILL.md"
    if not skill_md_path.exists():
        fail(f"SKILL.md not found in {skill_path}")

    name = read_skill_name(skill_md_path)

    output_dir = Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else skill_path.parent / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{name}.skill"

    included_skill_mds = []
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in skill_path.rglob("*"):
            if not f.is_file():
                continue
            rel_path = f.relative_to(skill_path)
            if not should_include(rel_path):
                continue
            if rel_path.name == "SKILL.md":
                included_skill_mds.append(str(rel_path))
            zf.write(f, arcname=str(Path(name) / rel_path))

    if len(included_skill_mds) != 1:
        output_path.unlink(missing_ok=True)
        fail(
            f"Refusing to package: found {len(included_skill_mds)} SKILL.md file(s) after "
            f"exclusions ({included_skill_mds}); expected exactly 1. Fix the skill directory "
            "or extend EXCLUDE_DIRS before repackaging."
        )

    print(json.dumps({"skill_name": name, "output_path": str(output_path)}, indent=2))


if __name__ == "__main__":
    main()
