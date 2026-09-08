#!/usr/bin/env python3
"""
structural_check.py — deterministic, machine-checkable analysis of a Claude
Agent Skill directory. This does NOT judge writing quality or triggering
strength (that's a qualitative pass Claude does afterward using
references/rubric.md) — it only computes objective facts and hard-compliance
errors so the qualitative review has real numbers to reason about instead of
re-deriving them by eye.

Usage:
    python structural_check.py <skill_directory>

Prints a single JSON object to stdout.
"""

import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(json.dumps({"fatal_error": "PyYAML not installed. Run: pip install pyyaml --break-system-packages"}))
    sys.exit(1)

ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
RESOURCE_DIRS = ("scripts", "references", "assets")
IMPERATIVE_MARKERS = ("MUST", "NEVER", "ALWAYS", "SHOULD", "REQUIRED", "DO NOT")
# Dev-only directories that never ship in the packaged skill (must mirror the exclude
# list in tools/package_skill.py at the solution root) — a fixture skill's own SKILL.md
# under one of these must not count against the "exactly one SKILL.md" packaging rule.
PACKAGING_EXCLUDE_DIRS = {"tests", ".git", "__pycache__", "dist", "node_modules", ".pytest_cache"}
PORTABILITY_PATTERNS = [
    r"/Users/[A-Za-z0-9_.-]+",
    r"/home/(?!claude\b)[A-Za-z0-9_.-]+",
    r"C:\\\\Users\\\\[A-Za-z0-9_.-]+",
]

# Recommended (not required) SKILL.md body section outline — see
# references/preferred-structure.md. Presence/absence is only ever reported
# as a soft signal, never a compliance_errors entry.
PREFERRED_SECTIONS = [
    "Purpose",
    "When to Use",
    "When NOT to Use",
    "Workflow",
    "Rules",
    "Decision Guidelines",
    "Validation",
    "References",
]

# Tool/MCP-usage cross-check vocabulary. Not exhaustive — a fixed, common-case
# list used to build *candidate* over/under-provisioning signals, same "needs
# human confirmation" treatment as orphaned_resource_files below.
KNOWN_TOOL_NAMES = (
    "Bash", "Read", "Write", "Edit", "Glob", "Grep",
    "WebFetch", "WebSearch", "NotebookEdit", "Agent", "Task",
)
MCP_TOOL_PATTERN = re.compile(r"\bmcp__[A-Za-z0-9_]+\b")

# Hardcoded secret/credential patterns. Matches are HARD ERRORS
# (compliance_errors) — unlike the other pattern groups below, this one skips
# the "candidate" treatment because the cost of shipping a real credential is
# high and these patterns are narrow enough that false positives are rare.
# Matched values are redacted before being reported.
SECRET_PATTERNS = [
    ("openai_style_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("aws_access_key_id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("jwt_like_token", re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
    ("private_key_block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("generic_api_key_or_secret", re.compile(
        r"(?i)(api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*['\"][^'\"]{12,}['\"]"
    )),
    ("connection_string_with_credentials", re.compile(
        r"(?i)(postgres|postgresql|mongodb|mysql|redis)://[^:@/\s]+:[^@/\s]+@"
    )),
]

# Dangerous shell/command patterns — candidates, surfaced as structural_warnings
# + metrics so the qualitative pass can confirm real risk vs. incidental match
# (e.g. `rm -rf` against a script's own scratch directory may be legitimate).
DANGEROUS_SHELL_PATTERNS = [
    ("rm_rf", re.compile(r"\brm\s+-rf\b")),
    ("pipe_to_shell", re.compile(r"\b(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(bash|sh)\b")),
    ("bare_eval", re.compile(r"\beval\(")),
    ("unrestricted_sudo", re.compile(r"\bsudo\s")),
    ("curl_insecure", re.compile(r"\bcurl\b[^\n]*(\s-k\b|--insecure\b)")),
    ("tls_verification_disabled", re.compile(
        r"verify\s*=\s*False|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|--no-check-certificate"
    )),
    ("chmod_777", re.compile(r"\bchmod\s+777\b")),
    ("git_ssl_verify_disabled", re.compile(r"sslVerify\s+false")),
    ("trusted_host_bypass", re.compile(r"--trusted-host\b")),
    ("unsigned_package_install", re.compile(r"--allow-unauthenticated|--nosignature")),
]

# Prompt-injection / instruction-override phrasing — candidates.
PROMPT_INJECTION_PATTERNS = [
    ("ignore_instructions", re.compile(r"(?i)ignore (all |any )?(previous|prior|system) instructions")),
    ("override_instructions", re.compile(r"(?i)overrides? (all|any) (prior|previous|system) instructions")),
    ("disregard_system_prompt", re.compile(r"(?i)disregard (the )?system prompt")),
    ("conceal_from_user", re.compile(r"(?i)(hide|conceal) this from the user")),
    ("without_user_knowledge", re.compile(r"(?i)without the user'?s knowledge")),
    ("fake_mode_claim", re.compile(r"(?i)you are now in [^.\n]*mode\b")),
    ("false_authority_claim", re.compile(r"(?i)trust me,? I am (the developer|anthropic|an admin)")),
]

# Prohibited-category action phrasing — candidates.
PROHIBITED_ACTION_PATTERNS = [
    ("enter_credentials_or_payment", re.compile(
        r"(?i)enter (your |the )?(password|credit card|ssn|social security)"
    )),
    ("bypass_captcha", re.compile(r"(?i)bypass (the )?captcha")),
    ("permanent_deletion", re.compile(r"(?i)permanently delete|empty the trash|hard[- ]delete")),
    ("financial_transfer", re.compile(r"(?i)wire transfer|send (money|funds|payment)")),
]

# Bare-URL extraction, used for the undeclared-external-host check.
URL_PATTERN = re.compile(r"https?://([A-Za-z0-9.-]+)(?:[:/][^\s'\"<>]*)?")


def fail(msg):
    print(json.dumps({"fatal_error": msg}))
    sys.exit(1)


def is_packaging_excluded(path, skill_path):
    """True if `path` sits under a dev-only/build-artifact directory (tests/,
    __pycache__, etc. — see PACKAGING_EXCLUDE_DIRS) or is compiled bytecode.
    These never ship in the packaged skill, so they shouldn't be counted as
    bundled resources, scanned for security patterns, or flagged as orphaned."""
    if path.suffix in (".pyc", ".pyo"):
        return True
    rel_parts = path.relative_to(skill_path).parts
    return any(part in PACKAGING_EXCLUDE_DIRS for part in rel_parts)


def parse_frontmatter(content, errors):
    if not content.startswith("---"):
        errors.append("No YAML frontmatter found (file must start with '---').")
        return {}
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        errors.append("Frontmatter delimiters found but block is malformed (missing closing '---').")
        return {}
    try:
        fm = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML in frontmatter: {e}")
        return {}
    if not isinstance(fm, dict):
        errors.append("Frontmatter must be a YAML dictionary/mapping.")
        return {}
    return fm


def check_skill_md_filename_case(skill_path, errors):
    """Path.exists()/read_text() are case-insensitive on Windows, so a file named
    e.g. 'Skill.md' or 'skill.md' would otherwise slip past unnoticed. Packaging
    and most non-Windows filesystems are case-sensitive, so this must be exact."""
    try:
        entries = os.listdir(skill_path)
    except OSError:
        return
    if "SKILL.md" in entries:
        return
    wrong_case = [e for e in entries if e.lower() == "skill.md"]
    if wrong_case:
        errors.append(
            f"Skill file is named '{wrong_case[0]}' but must be exactly 'SKILL.md' "
            "(case-sensitive on packaging and most non-Windows filesystems)."
        )


def check_name(name, folder_name, errors, warnings):
    if not name:
        errors.append("Missing 'name' in frontmatter.")
        return
    if not isinstance(name, str):
        errors.append(f"'name' must be a string, got {type(name).__name__}.")
        return
    name = name.strip()
    if not re.match(r"^[a-z0-9-]+$", name):
        errors.append(f"Name '{name}' should be kebab-case (lowercase letters, digits, hyphens only).")
    if name.startswith("-") or name.endswith("-") or "--" in name:
        errors.append(f"Name '{name}' cannot start/end with a hyphen or contain consecutive hyphens.")
    if len(name) > 64:
        errors.append(f"Name is {len(name)} characters; max is 64.")
    if folder_name and name != folder_name:
        warnings.append(
            f"Frontmatter name '{name}' does not match containing folder name '{folder_name}'. "
            "These should generally match for clarity and correct packaging."
        )


def check_description(description, errors, warnings, metrics):
    if not description:
        errors.append("Missing 'description' in frontmatter.")
        return
    if not isinstance(description, str):
        errors.append(f"'description' must be a string, got {type(description).__name__}.")
        return
    description = description.strip()
    if "<" in description or ">" in description:
        errors.append("Description cannot contain angle brackets (< or >).")
    if len(description) > 1024:
        errors.append(f"Description is {len(description)} characters; max is 1024.")
    word_count = len(description.split())
    metrics["description_length_chars"] = len(description)
    metrics["description_word_count"] = word_count
    if word_count < 8:
        warnings.append(
            f"Description is only {word_count} words. This is the sole triggering signal Claude "
            "sees before deciding to consult the skill — it likely doesn't cover both WHAT the "
            "skill does and WHEN to use it."
        )
    # Heuristic: does it read like it covers a triggering condition, not just a capability?
    trigger_cue_pattern = re.compile(
        r"\b(when|whenever|use (this|it) (when|for|to)|trigger|if the user|any time)\b", re.IGNORECASE
    )
    metrics["description_has_trigger_cue"] = bool(trigger_cue_pattern.search(description))
    if not metrics["description_has_trigger_cue"]:
        warnings.append(
            "Description doesn't contain an obvious 'when to use this' cue (e.g. 'when', "
            "'use this whenever...'). Descriptions that only state capability tend to under-trigger."
        )


def check_metadata_version(frontmatter, warnings):
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict) or not str(metadata.get("version") or "").strip():
        warnings.append(
            "No 'metadata.version' set. Recommended so review reports and packaging can track "
            "skill revisions over time."
        )


def check_preferred_structure_sections(body):
    """Soft signal only — see references/preferred-structure.md. A missing
    section is never a compliance error; many skills legitimately don't need
    all eight (e.g. no meaningful 'When NOT to Use')."""
    present = []
    missing = []
    for section in PREFERRED_SECTIONS:
        pattern = re.compile(rf"^#{{1,2}}\s+{re.escape(section)}\b", re.IGNORECASE | re.MULTILINE)
        (present if pattern.search(body) else missing).append(section)
    return {"present": present, "missing": missing}


def scan_body_for_resource_mentions(body, resource_files):
    """Flag bundled resource files that are never referenced by name in the SKILL.md body."""
    orphaned = []
    for rel_path in resource_files:
        filename = Path(rel_path).name
        if filename not in body and rel_path not in body:
            orphaned.append(rel_path)
    return orphaned


def check_large_references_for_toc(references_dir):
    flagged = []
    if not references_dir.is_dir():
        return flagged
    for f in references_dir.rglob("*"):
        if f.is_file() and f.suffix.lower() in (".md", ".txt"):
            try:
                text = f.read_text(errors="ignore")
            except Exception:
                continue
            line_count = text.count("\n") + 1
            if line_count > 300:
                has_toc = bool(re.search(r"table of contents|## contents\b", text, re.IGNORECASE))
                if not has_toc:
                    flagged.append({"file": str(f.relative_to(references_dir.parent)), "lines": line_count})
    return flagged


def find_portability_issues(text):
    issues = []
    for pattern in PORTABILITY_PATTERNS:
        for m in re.finditer(pattern, text):
            issues.append(m.group(0))
    return sorted(set(issues))


def count_imperative_markers(body):
    counts = {}
    for marker in IMPERATIVE_MARKERS:
        counts[marker] = len(re.findall(rf"\b{re.escape(marker)}\b", body))
    return counts


def extract_must_never_lines(body):
    """Pull out every line containing a MUST or NEVER directive, with its line number and
    text, so the qualitative pass can review each one individually rather than working from
    a bare count. MUST/NEVER (not the full IMPERATIVE_MARKERS set) because these are the two
    that read as hard boundaries — see rubric.md's hook-vs-prose guidance for what to do with
    each: a skill can't enforce its own hook, so the fix is never "remove this," but a hard
    directive protecting against real harm resting on prose alone (which the model could be
    talked past) is worth flagging for a companion hook recommendation."""
    marker_pattern = re.compile(r"\b(MUST|NEVER)\b")
    lines = []
    for i, line in enumerate(body.split("\n"), start=1):
        markers = sorted(set(marker_pattern.findall(line)))
        if markers:
            lines.append({"line": i, "markers": markers, "text": line.strip()})
    return lines


def gather_scannable_files(skill_path, body):
    """(relative_path, text) pairs for the SKILL.md body plus every file under
    scripts/ — the shared corpus for the tool-usage and security pattern scans
    below, so they all see the same file+line context."""
    files = [("SKILL.md", body)]
    scripts_dir = skill_path / "scripts"
    if scripts_dir.is_dir():
        for f in sorted(scripts_dir.rglob("*")):
            if f.is_file() and not is_packaging_excluded(f, skill_path):
                try:
                    text = f.read_text(errors="ignore")
                except Exception:
                    continue
                files.append((str(f.relative_to(skill_path)), text))
    return files


def compute_tool_usage(frontmatter, body):
    declared_raw = frontmatter.get("allowed-tools")
    if isinstance(declared_raw, str):
        declared = [t.strip() for t in declared_raw.split(",") if t.strip()]
    elif isinstance(declared_raw, list):
        declared = [str(t).strip() for t in declared_raw if str(t).strip()]
    else:
        declared = []
    declared_set = set(declared)

    referenced = set()
    for name in KNOWN_TOOL_NAMES:
        if re.search(rf"\b{re.escape(name)}\b", body):
            referenced.add(name)
    referenced.update(MCP_TOOL_PATTERN.findall(body))

    declared_but_unreferenced = sorted(t for t in declared_set if t not in referenced)
    # Only meaningful once allowed-tools is actually declared — with no frontmatter
    # restriction at all there's no "undeclared" tool to flag.
    referenced_but_undeclared = sorted(t for t in referenced if declared_set and t not in declared_set)
    return declared, declared_but_unreferenced, referenced_but_undeclared


def scan_for_secrets(files):
    hits = []
    for rel_path, text in files:
        for line_no, line in enumerate(text.split("\n"), start=1):
            for category, regex in SECRET_PATTERNS:
                m = regex.search(line)
                if m:
                    matched = m.group(0)
                    redacted = (matched[:4] + "…redacted…") if len(matched) > 4 else "…redacted…"
                    hits.append({"file": rel_path, "line": line_no, "category": category, "redacted_match": redacted})
    return hits


def scan_patterns(files, patterns):
    hits = []
    for rel_path, text in files:
        for line_no, line in enumerate(text.split("\n"), start=1):
            for category, regex in patterns:
                m = regex.search(line)
                if m:
                    hits.append({"file": rel_path, "line": line_no, "category": category, "match": m.group(0)})
    return hits


def find_undeclared_external_hosts(files, description):
    """Hostnames referenced anywhere in the body/scripts that never appear in the
    frontmatter description — the description is the skill's stated purpose, so a
    host contacted without ever being named there is a candidate worth reviewing."""
    hosts = set()
    for _rel_path, text in files:
        hosts.update(URL_PATTERN.findall(text))
    description = description or ""
    return sorted(h for h in hosts if h not in description)


def main():
    if len(sys.argv) != 2:
        fail("Usage: python structural_check.py <skill_directory>")

    skill_path = Path(sys.argv[1])
    if not skill_path.is_dir():
        fail(f"Not a directory: {skill_path}")

    skill_md_path = skill_path / "SKILL.md"
    if not skill_md_path.exists():
        fail(f"SKILL.md not found in {skill_path}")

    content = skill_md_path.read_text(errors="ignore")
    errors = []
    warnings = []
    metrics = {}

    frontmatter = parse_frontmatter(content, errors)

    unexpected_keys = set(frontmatter.keys()) - ALLOWED_FRONTMATTER_KEYS
    if unexpected_keys:
        errors.append(
            f"Unexpected frontmatter key(s): {', '.join(sorted(unexpected_keys))}. "
            f"Allowed: {', '.join(sorted(ALLOWED_FRONTMATTER_KEYS))}."
        )

    check_skill_md_filename_case(skill_path, errors)
    check_name(frontmatter.get("name", ""), skill_path.name, errors, warnings)
    check_description(frontmatter.get("description", ""), errors, warnings, metrics)
    check_metadata_version(frontmatter, warnings)

    # Body = everything after the closing '---' of frontmatter
    body_match = re.match(r"^---\n.*?\n---\n(.*)$", content, re.DOTALL)
    body = body_match.group(1) if body_match else content

    body_line_count = body.count("\n") + 1
    metrics["skill_md_total_line_count"] = content.count("\n") + 1
    metrics["skill_md_body_line_count"] = body_line_count
    if body_line_count > 500:
        warnings.append(
            f"SKILL.md body is {body_line_count} lines (guideline: keep under ~500, ideally with an "
            "extra layer of hierarchy — e.g. references/ files — once you approach this)."
        )

    preferred_sections = check_preferred_structure_sections(body)
    metrics["preferred_structure_sections"] = preferred_sections
    if preferred_sections["missing"]:
        warnings.append(
            f"{len(preferred_sections['present'])} of {len(PREFERRED_SECTIONS)} recommended SKILL.md "
            "sections found (see references/preferred-structure.md) — missing: "
            + ", ".join(preferred_sections["missing"])
            + ". This is a soft recommendation, not every skill needs all of them."
        )

    # Multiple SKILL.md check (mirrors packaging requirement: exactly one, at <folder>/SKILL.md).
    # Ignore dev-only dirs (e.g. tests/fixtures/*) since package_skill.py strips them before
    # packaging — a bundled fixture skill's SKILL.md isn't a real violation.
    all_skill_mds = [p for p in skill_path.rglob("SKILL.md")]
    shipped_skill_mds = [p for p in all_skill_mds if not is_packaging_excluded(p, skill_path)]
    excluded_skill_mds = [p for p in all_skill_mds if is_packaging_excluded(p, skill_path)]
    if len(shipped_skill_mds) > 1:
        errors.append(
            f"Found {len(shipped_skill_mds)} SKILL.md files that would ship in the package "
            f"(outside {sorted(PACKAGING_EXCLUDE_DIRS)}); a packaged skill must contain exactly "
            "one, at <folder>/SKILL.md."
        )
    if excluded_skill_mds:
        metrics_note = [str(p.relative_to(skill_path)) for p in excluded_skill_mds]
    else:
        metrics_note = []

    metrics["dev_only_skill_mds_excluded"] = metrics_note

    # Resource directory presence + per-directory file counts
    dirs_present = {d: (skill_path / d).is_dir() for d in RESOURCE_DIRS}
    metrics["resource_dirs_present"] = dirs_present

    resource_files = []
    resource_dir_file_counts = {}
    for d in RESOURCE_DIRS:
        dpath = skill_path / d
        count = 0
        if dpath.is_dir():
            for f in dpath.rglob("*"):
                if f.is_file() and not is_packaging_excluded(f, skill_path):
                    resource_files.append(str(f.relative_to(skill_path)))
                    count += 1
        resource_dir_file_counts[d] = count
    metrics["resource_file_count"] = len(resource_files)
    metrics["resource_dir_file_counts"] = resource_dir_file_counts

    orphaned = scan_body_for_resource_mentions(body, resource_files)
    if orphaned:
        warnings.append(
            "Bundled resource file(s) are never mentioned by name in the SKILL.md body, so Claude "
            f"has no pointer telling it when to read them: {', '.join(orphaned)}."
        )
    metrics["orphaned_resource_files"] = orphaned

    large_refs_missing_toc = check_large_references_for_toc(skill_path / "references")
    if large_refs_missing_toc:
        warnings.append(
            "Reference file(s) over 300 lines have no visible table of contents: "
            + ", ".join(f"{r['file']} ({r['lines']} lines)" for r in large_refs_missing_toc)
        )
    metrics["large_reference_files_missing_toc"] = large_refs_missing_toc

    portability_issues = find_portability_issues(content)
    if portability_issues:
        warnings.append(
            "Hardcoded user-specific/absolute paths found — these will break for other users: "
            + ", ".join(portability_issues)
        )
    metrics["portability_issues"] = portability_issues

    metrics["imperative_marker_counts"] = count_imperative_markers(body)

    must_never_lines = extract_must_never_lines(body)
    metrics["must_never_lines"] = must_never_lines
    if must_never_lines:
        warnings.append(
            f"{len(must_never_lines)} line(s) contain a MUST/NEVER directive (see "
            "metrics.must_never_lines for the full list with line numbers) — review each "
            "against rubric.md's guidance on whether it protects against real harm and should "
            "therefore also be recommended as a Claude Code hook, not left to rest on prose alone."
        )

    # --- Tool/MCP usage cross-check (candidates) ---
    declared_tools, declared_but_unreferenced, referenced_but_undeclared = compute_tool_usage(frontmatter, body)
    metrics["declared_tools"] = declared_tools
    metrics["tools_declared_but_unreferenced"] = declared_but_unreferenced
    metrics["tools_referenced_but_undeclared"] = referenced_but_undeclared
    if declared_but_unreferenced:
        warnings.append(
            "Tool(s) declared in 'allowed-tools' but never referenced in the SKILL.md body — "
            "candidate over-provisioning, broadening attack surface without a stated need: "
            + ", ".join(declared_but_unreferenced)
        )
    if referenced_but_undeclared:
        warnings.append(
            "Tool(s) referenced in the SKILL.md body but not listed in 'allowed-tools' — "
            "candidate under-provisioning, may fail at runtime: "
            + ", ".join(referenced_but_undeclared)
        )

    # --- Security pattern scans (SKILL.md body + everything under scripts/) ---
    scannable_files = gather_scannable_files(skill_path, body)

    secret_hits = scan_for_secrets(scannable_files)
    if secret_hits:
        for hit in secret_hits:
            errors.append(
                f"Possible hardcoded secret/credential ({hit['category']}) at "
                f"{hit['file']}:{hit['line']} — value redacted ({hit['redacted_match']}). "
                "Remove hardcoded credentials before publishing."
            )
    metrics["hardcoded_secret_candidates"] = secret_hits

    dangerous_shell_hits = scan_patterns(scannable_files, DANGEROUS_SHELL_PATTERNS)
    metrics["dangerous_shell_pattern_candidates"] = dangerous_shell_hits
    if dangerous_shell_hits:
        warnings.append(
            f"{len(dangerous_shell_hits)} potentially dangerous shell pattern(s) found (see "
            "metrics.dangerous_shell_pattern_candidates) — confirm each is actually needed and "
            "safe in context before treating it as a finding."
        )

    prompt_injection_hits = scan_patterns(scannable_files, PROMPT_INJECTION_PATTERNS)
    metrics["prompt_injection_phrase_candidates"] = prompt_injection_hits
    if prompt_injection_hits:
        warnings.append(
            f"{len(prompt_injection_hits)} phrase(s) resembling prompt-injection/instruction-override "
            "language found (see metrics.prompt_injection_phrase_candidates) — review context before "
            "treating as a finding."
        )

    prohibited_action_hits = scan_patterns(scannable_files, PROHIBITED_ACTION_PATTERNS)
    metrics["prohibited_action_phrase_candidates"] = prohibited_action_hits
    if prohibited_action_hits:
        warnings.append(
            f"{len(prohibited_action_hits)} phrase(s) resembling a prohibited high-risk action found "
            "(see metrics.prohibited_action_phrase_candidates) — review context before treating as a finding."
        )

    undeclared_hosts = find_undeclared_external_hosts(scannable_files, frontmatter.get("description"))
    metrics["undeclared_external_hosts"] = undeclared_hosts
    if undeclared_hosts:
        warnings.append(
            "External host(s) referenced in the body/scripts but never mentioned in the frontmatter "
            "description (the skill's stated purpose): " + ", ".join(undeclared_hosts)
        )

    result = {
        "skill_path": str(skill_path),
        "frontmatter": frontmatter,
        "compliance_errors": errors,
        "structural_warnings": warnings,
        "metrics": metrics,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
