"""A stand-in for `claude -p ... --output-format stream-json` used by the tests. Spends no tokens.

Behaviour is set by environment variables:
    FAKE_FAIL_CASE   input file name that gets an error result
    FAKE_MODE        "hang" sleeps long (timeout test), "silent" prints nothing, "ok" (default)
It also fails when the evals folder is visible from the working directory, so the tests prove isolation.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

args = sys.argv[1:]
prompt = args[args.index("-p") + 1]
model = args[args.index("--model") + 1]
case = (re.search(r"file (\S+?)\. Reply", prompt) or re.search(r"(\S+\.md)", prompt)).group(1)
mode = os.environ.get("FAKE_MODE", "ok")

if mode == "hang":
    time.sleep(60)
if mode == "silent":
    sys.exit(1)


def emit(obj):
    print(json.dumps(obj), flush=True)


emit({"type": "system", "subtype": "init", "model": model})
leaked = any(Path(".claude", "skills").glob("*/evals")) or Path("evals").exists()
usage = {"input_tokens": 100, "output_tokens": 50, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 10}
if leaked or case == os.environ.get("FAKE_FAIL_CASE"):
    emit({"type": "result", "subtype": "success", "is_error": True, "result": "evals visible" if leaked else "boom",
          "usage": usage, "total_cost_usd": 0.01, "duration_ms": 1000, "num_turns": 1})
    sys.exit(0)
emit({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "x"}},
                                                    {"type": "tool_use", "name": "Read", "input": {}}]}})
text = Path(case).read_text(encoding="utf-8")
emit({"type": "result", "subtype": "success", "is_error": False, "result": f"{model}: " + text, "usage": usage,
      "total_cost_usd": 0.25, "duration_ms": 2000, "num_turns": 3})
