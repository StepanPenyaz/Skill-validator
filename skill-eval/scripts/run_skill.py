#!/usr/bin/env python3
"""
run_skill.py - runs the target skill on every eval input, on every model, several
times, each case in its own clean `claude -p` process. No orchestrating model.

Usage:
    python run_skill.py <skill_dir> [--models opus,sonnet] [--runs X] [--jobs N] [--profile document]
                        [--cases 01-a.md,02-b.md] [--force] [--claude-bin <command>]

Reads from <skill_dir>:
    SKILL.md, the skill's files          copied into a temporary project as .claude/skills/<name>/
                                         (evals/, step_reports/, reports are left out, so the
                                         verified outputs can never be seen by the model)
    evals/inputs/*                       one case per file
    config.yaml                          default_models, runs_per_model, runner limits, and the profile (prompt, tools)

Writes, under <skill_dir>/evals/<skill>_<version>_outputs/:
    <model>/run_<r>/<case>               the produced output (only when the case succeeded)
    <model>/run_<r>/<case>.json          status, tokens (input/output/cache), real cost, time, turns, tools
    <model>/run_<r>/<case>.jsonl         the full transcript (stream-json)
    run_on_<model>_report.md             numbers per full run, averaged over the runs

A case that fails (error, timeout, budget, empty output) is recorded as failed and
the other cases and runs go on. Cases that already succeeded are skipped unless
--force is given, so an interrupted evaluation can be resumed.

The command used is the one named in --claude-bin or the CLAUDE_BIN environment
variable (default: claude), which lets tests use a fake executable.
"""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profiles import get_profile  # noqa: E402
from build_final_report import fmt_cost, fmt_time, load_config as load_shared_config, skill_meta  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

SKIP_IN_SKILL_COPY = {"evals", "step_reports", "static_report", "dist", ".git", "__pycache__", "node_modules",
                      "final_report.md", "detailed_final_report.md"}
DEFAULTS = {"runs_per_model": 3,
            "runner": {"jobs": 3, "timeout_seconds": 600, "max_budget_usd": 1.0}}


# ---------- config ----------

def load_config():
    cfg = load_shared_config()
    runner = {**DEFAULTS["runner"], **(cfg.get("runner") or {})}
    return {"models": cfg.get("default_models") or [], "runs": int(cfg.get("runs_per_model", DEFAULTS["runs_per_model"])),
            "runner": runner}


def list_cases(skill_dir, only=None):
    files = sorted(p for p in (Path(skill_dir) / "evals" / "inputs").glob("*") if p.is_file())
    if only:
        files = [f for f in files if f.name in only]
    return files


def build_prompt(profile, input_name):
    """The request given to the model: the profile's prompt with {input_file} filled in."""
    return profile.run_options()["prompt"].replace("{input_file}", input_name)


# ---------- one case ----------

def install_skill(skill_dir, workdir, name):
    target = Path(workdir) / ".claude" / "skills" / name
    shutil.copytree(skill_dir, target, ignore=lambda _d, names: [n for n in names if n in SKIP_IN_SKILL_COPY])


def parse_stream(text):
    """Result event and tool use of one stream-json transcript. Pure function.

    Returns {result: dict | None, tool_calls: Counter}. Lines that are not JSON are skipped.
    """
    result, tools = None, Counter()
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "result":
            result = event
        elif event.get("type") == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tools[block.get("name") or "unknown"] += 1
    return {"result": result, "tool_calls": tools}


def summarize_case(text, exit_code, model, run, case, timed_out=None, stderr=""):
    """Case summary (what is saved as <case>.json) from the transcript text. Pure function."""
    parsed = parse_stream(text)
    res = parsed["result"]
    out = {"model": model, "run": run, "case": case, "status": "failed", "reason": "", "output": "",
           "tokens": None, "cost_usd": None, "duration_ms": None, "num_turns": None,
           "tool_calls": dict(parsed["tool_calls"]), "skill_loaded": "Skill" in parsed["tool_calls"]}
    if timed_out:
        out["reason"] = f"timeout after {timed_out}s"
    if res is None:
        last = (stderr.strip().splitlines() or [""])[-1][:160]
        out["reason"] = out["reason"] or f"no result event (exit code {exit_code})" + (f": {last}" if last else "")
        return out
    usage = res.get("usage") or {}
    parts = {"input": usage.get("input_tokens"), "output": usage.get("output_tokens"),
             "cache_read": usage.get("cache_read_input_tokens"), "cache_creation": usage.get("cache_creation_input_tokens")}
    if all(isinstance(v, (int, float)) for v in parts.values()):
        out["tokens"] = {**{k: int(v) for k, v in parts.items()}, "total": int(sum(parts.values()))}
    cost = res.get("total_cost_usd")
    out["cost_usd"] = float(cost) if isinstance(cost, (int, float)) else None
    out["duration_ms"] = res.get("duration_ms") if isinstance(res.get("duration_ms"), (int, float)) else None
    out["num_turns"] = res.get("num_turns")
    answer = res.get("result") if isinstance(res.get("result"), str) else ""
    if timed_out:
        return out
    if res.get("is_error"):
        out["reason"] = (answer or res.get("terminal_reason") or "error result")[:200]
    elif res.get("subtype") not in (None, "success"):
        out["reason"] = str(res.get("subtype"))
    elif not answer.strip():
        out["reason"] = "empty output"
    else:
        out["status"], out["output"] = "ok", answer
    return out


def case_paths(out_dir, model, run, case):
    d = Path(out_dir) / model / f"run_{run}"
    return d / case, d / f"{case}.json", d / f"{case}.jsonl"


def run_case(job, claude_cmd, skill_dir, out_dir, runner, force=False, profile=None):
    profile = profile or get_profile()
    model, run, input_path = job
    case = input_path.name
    out_path, json_path, log_path = case_paths(out_dir, model, run, case)
    if not force and json_path.is_file():
        try:
            if json.loads(json_path.read_text(encoding="utf-8")).get("status") == "ok" and out_path.is_file():
                return json.loads(json_path.read_text(encoding="utf-8"))
        except ValueError:
            pass
    name = skill_meta(skill_dir)["name"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="skill-eval-") as work:
        install_skill(skill_dir, work, name)
        shutil.copy2(input_path, Path(work) / case)
        cmd = claude_cmd + ["-p", build_prompt(profile, case), "--model", model,
                            "--output-format", "stream-json", "--verbose", "--no-session-persistence",
                            "--permission-mode", "dontAsk", "--max-budget-usd", str(runner["max_budget_usd"]),
                            "--allowedTools=" + ",".join(profile.run_options()["allowed_tools"])]
        timed_out = None
        try:
            proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                  stdin=subprocess.DEVNULL, timeout=runner["timeout_seconds"])
            text, code, err = proc.stdout, proc.returncode, proc.stderr
        except subprocess.TimeoutExpired as e:
            raw = e.stdout or b""
            text, code, timed_out = (raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw), None, runner["timeout_seconds"]
            err = ""
        summary = summarize_case(text, code, model, run, case, timed_out, err)
        if summary["status"] == "ok":  # the profile decides where the output comes from (here: the reply)
            collected = profile.collect(summary["output"], work)
            if str(collected or "").strip():
                summary["output"] = collected
            else:
                summary["status"], summary["reason"], summary["output"] = "failed", "empty output", ""
    log_path.write_text(text, encoding="utf-8")
    if summary["status"] == "ok":
        out_path.write_text(summary["output"], encoding="utf-8")
    elif out_path.is_file():
        out_path.unlink()
    summary_on_disk = {k: v for k, v in summary.items() if k != "output"}
    json_path.write_text(json.dumps(summary_on_disk, indent=2), encoding="utf-8")
    return summary


# ---------- reports ----------

def read_case_summaries(out_dir, model, cases):
    """{run: {case: summary | None}} from the saved <case>.json files of one model."""
    runs = {}
    for run_dir in sorted(Path(out_dir, model).glob("run_*"), key=lambda p: int(p.name[4:]) if p.name[4:].isdigit() else 0):
        r = int(run_dir.name[4:]) if run_dir.name[4:].isdigit() else None
        if r is None:
            continue
        runs[r] = {}
        for case in cases:
            f = run_dir / f"{case}.json"
            try:
                runs[r][case] = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None
            except ValueError:
                runs[r][case] = None
    return runs


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def aggregate_model(runs, cases):
    """Per-run totals and their means. A number is None when any case of the run did not report it."""
    per_run = []
    for r, by_case in sorted(runs.items()):
        s = [by_case.get(c) for c in cases]
        ok = all(x is not None and x.get("status") == "ok" for x in s)

        def total(getter):
            vals = [getter(x) if x else None for x in s]
            return None if any(v is None for v in vals) else sum(vals)
        per_run.append({
            "run": r, "valid": ok, "failed": sum(1 for x in s if x is None or x.get("status") != "ok"),
            "tokens": total(lambda x: (x.get("tokens") or {}).get("total")),
            "input": total(lambda x: (x.get("tokens") or {}).get("input")),
            "output": total(lambda x: (x.get("tokens") or {}).get("output")),
            "cache_read": total(lambda x: (x.get("tokens") or {}).get("cache_read")),
            "cache_creation": total(lambda x: (x.get("tokens") or {}).get("cache_creation")),
            "seconds": (lambda v: None if v is None else v / 1000)(total(lambda x: x.get("duration_ms"))),
            "cost": total(lambda x: x.get("cost_usd")),
            "turns": total(lambda x: x.get("num_turns")),
            "tool_calls": sum(sum((x.get("tool_calls") or {}).values()) for x in s if x),
            "skill_loaded": sum(1 for x in s if x and x.get("skill_loaded")),
        })
    return per_run


def render_run_report(model, per_run, n_cases):
    def mean_of(key):
        return _mean([r[key] for r in per_run])

    def num(v, fmt):
        return "unavailable" if v is None else fmt(v)
    runs, valid = len(per_run), sum(1 for r in per_run if r["valid"])
    loaded = sum(r["skill_loaded"] for r in per_run)
    lines = [f"# Run report: {model}", f"- Model name: {model}",
             f"- Tokens used: {num(mean_of('tokens'), lambda v: str(int(round(v))))}",
             f"- Time spent: {num(mean_of('seconds'), fmt_time)}",
             f"- Total cost: {num(mean_of('cost'), fmt_cost)}",
             f"- Runs: {runs}", f"- Complete runs: {valid}",
             f"- Failed cases: {sum(r['failed'] for r in per_run)} of {runs * n_cases}"]
    for label, key in (("Input tokens", "input"), ("Output tokens", "output"),
                       ("Cache read tokens", "cache_read"), ("Cache creation tokens", "cache_creation"),
                       ("Turns", "turns"), ("Tool calls", "tool_calls")):
        lines.append(f"- {label}: {num(mean_of(key), lambda v: str(int(round(v))))}")
    lines.append(f"- Skill loaded: {loaded} of {runs * n_cases} cases")
    lines += ["", "Tokens, time, cost, turns and tool calls are means per full run (all cases). Tokens are input + output + "
              "cache read + cache creation as reported by `claude -p`; cost is the cost it reports."]
    return "\n".join(lines) + "\n"


def write_reports(skill_dir, models, cases):
    meta = skill_meta(skill_dir)
    out_dir = Path(skill_dir) / "evals" / f"{meta['name']}_{meta['version']}_outputs"
    for model in models:
        per_run = aggregate_model(read_case_summaries(out_dir, model, cases), cases)
        if per_run:
            (out_dir / f"run_on_{model}_report.md").write_text(render_run_report(model, per_run, len(cases)), encoding="utf-8")
    return out_dir


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Run a skill on every eval input, model and repeat with `claude -p`.")
    ap.add_argument("skill_dir")
    ap.add_argument("--models", help="comma-separated; default: default_models of config.yaml")
    ap.add_argument("--runs", type=int, help="repeats per model; default: runs_per_model")
    ap.add_argument("--jobs", type=int, help="processes at the same time; default: runner.jobs")
    ap.add_argument("--cases", help="comma-separated input file names (default: all)")
    ap.add_argument("--force", action="store_true", help="run again cases that already succeeded")
    ap.add_argument("--profile", help="profile of the kind of skill; default: default_profile of config.yaml")
    ap.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"))
    args = ap.parse_args()

    skill_dir = Path(args.skill_dir)
    if not (skill_dir / "SKILL.md").is_file():
        sys.exit(f"Error: no SKILL.md in {skill_dir}")
    cfg = load_config()
    profile = get_profile(args.profile)
    ok, note = profile.check_applicable(skill_dir)
    if not ok:
        sys.exit(f"Error: profile '{profile.name}' cannot judge this skill: {note}")
    models =[m.strip() for m in (args.models or "").split(",") if m.strip()] or cfg["models"]
    runs = args.runs or cfg["runs"]
    cases = list_cases(skill_dir, set(args.cases.split(",")) if args.cases else None)
    if not models or not cases or runs < 1:
        sys.exit("Error: need at least one model, one input in evals/inputs/ and runs >= 1.")
    # a path to an executable is used as is (it may contain spaces); anything else is split like a shell command
    cmd = [args.claude_bin] if os.path.exists(args.claude_bin) else shlex.split(args.claude_bin)
    resolved = shutil.which(cmd[0])
    if resolved is None:
        sys.exit(f"Error: command not found: {cmd[0]}")
    cmd[0] = resolved

    meta = skill_meta(skill_dir)
    out_dir = skill_dir / "evals" / f"{meta['name']}_{meta['version']}_outputs"
    jobs = [(m, r, c) for m in models for r in range(1, runs + 1) for c in cases]
    print(f"{len(jobs)} case run(s): {len(models)} model(s) x {runs} run(s) x {len(cases)} input(s), "
          f"{args.jobs or cfg['runner']['jobs']} at a time")
    with ThreadPoolExecutor(max_workers=args.jobs or cfg["runner"]["jobs"]) as pool:
        futures = [pool.submit(run_case, j, cmd, skill_dir, out_dir, cfg["runner"], args.force, profile) for j in jobs]
        failed = 0
        for job, fut in zip(jobs, futures):
            try:
                s = fut.result()
            except Exception as e:  # one broken launch must not stop the others
                s = {"status": "failed", "reason": f"runner error: {e}"}
            failed += s["status"] != "ok"
            print(f"  {job[0]} run {job[1]} {job[2].name}: {s['status']}" + (f" ({s['reason']})" if s.get("reason") else ""))
    out_dir = write_reports(skill_dir, models, [c.name for c in cases])
    print(f"Done: {len(jobs) - failed} ok, {failed} failed. Reports in {out_dir}")


if __name__ == "__main__":
    main()
