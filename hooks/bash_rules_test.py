#!/usr/bin/env python3
"""Check bash-rules.py end to end: the hook input it reads, and the PreToolUse output it writes.

Run `python3 ~/.claude/hooks/bash_rules_test.py` after editing the hook.
Each rule's own test covers which commands it denies, so the cases here cover only what passes through the hook.
A hook that crashes writes nothing to stdout, which the PreToolUse caller reads as allowing the command unchanged, so a failing case prints the hook's stderr.
"""

import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from hook_testing import report
from foreground_timeout import FOREGROUND_TIMEOUT_MS, KILLED_AT_TIMEOUT_PREFIX

HOOK = str(Path(__file__).with_name("bash-rules.py"))
ON_DENIAL = importlib.import_module("bash-rules").ON_DENIAL


def reason_count(denial):
    """Return how many rules' reasons the hook's denial text gives, or None when a denial does not end with `ON_DENIAL`."""
    if not denial:
        return 0
    *reasons, last = denial.splitlines()
    return len(reasons) if last == ON_DENIAL else None


def run_hook(stdin):
    """Return (`reason_count` of the hook's denial of the command in `stdin`, the tool input it runs the call with or None, the hook's stderr)."""
    result = subprocess.run([sys.executable, HOOK], input=stdin, capture_output=True, text=True)
    if not result.stdout.strip():
        return 0, None, result.stderr
    output = json.loads(result.stdout)["hookSpecificOutput"]
    return reason_count(output.get("permissionDecisionReason")), output.get("updatedInput"), result.stderr


def tool_input(command, timeout=None, run_in_background=False):
    """Return a Bash tool input holding `timeout` and `run_in_background` only when given."""
    timeout_entry = {} if timeout is None else {"timeout": timeout}
    background_entry = {"run_in_background": True} if run_in_background else {}
    return {"command": command} | timeout_entry | background_entry


def killed_at(command, timeout):
    """Return the tool input of a foreground call that Claude Code kills after `timeout` milliseconds."""
    return tool_input(KILLED_AT_TIMEOUT_PREFIX + command, timeout)


def hook_input(command, cwd, timeout=None, run_in_background=False):
    return json.dumps({"tool_name": "Bash", "tool_input": tool_input(command, timeout, run_in_background), "cwd": str(cwd)})


def main():
    with tempfile.TemporaryDirectory() as root:
        project = Path(root)
        (project / ".venv").mkdir()
        (project / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin\n")
        # Each case is (hook input, how many rules the command breaks, the tool input the call runs with or None).
        cases = [
            (hook_input("ls src", project), 0, killed_at("ls src", FOREGROUND_TIMEOUT_MS)),
            (hook_input("grep -n TODO src/main.py", project), 1, None),
            (hook_input("cd src", project), 1, None),
            # A command breaking several rules gets every rule's reason.
            (hook_input("cd src && grep -n TODO main.py", project), 2, None),
            # The venv rule reads `cwd` from the hook input.
            (hook_input("python3 x.py", project), 1, None),
            (hook_input("python3 x.py", project.parent), 0, killed_at("python3 x.py", FOREGROUND_TIMEOUT_MS)),
            # A foreground call is killed after at most the foreground timeout.
            (hook_input("ls", project, timeout=600000), 0, killed_at("ls", FOREGROUND_TIMEOUT_MS)),
            (hook_input("ls", project, timeout=1000), 0, killed_at("ls", 1000)),
            (hook_input("ls", project, timeout=0), 0, killed_at("ls", FOREGROUND_TIMEOUT_MS)),
            # The rules judge the command Claude sent, so the added `sleep 0` does not put a command before a commit.
            (hook_input("git commit -m x", project), 0, killed_at("git commit -m x", FOREGROUND_TIMEOUT_MS)),
            # A background call runs unchanged.
            (hook_input("ls", project, timeout=600000, run_in_background=True), 0, None),
            # Input that is not a JSON object allows the command unchanged.
            ("not json", 0, None),
        ]
        failures = 0
        for stdin, broken, runs_with in cases:
            reasons, updated, stderr = run_hook(stdin)
            if (reasons, updated) == (broken, runs_with):
                continue
            failures += 1
            print(f"FAIL want {broken} reasons and {runs_with}, got {reasons} and {updated}: {stdin}")
            if stderr.strip():
                print(f"    {stderr.strip().splitlines()[-1]}")
    report(failures, len(cases))


if __name__ == "__main__":
    main()
