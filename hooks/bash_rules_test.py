#!/usr/bin/env python3
"""Check bash-rules.py end to end: the hook input it reads, and the PreToolUse decision it writes.

Run `python3 ~/.claude/hooks/bash_rules_test.py` after editing the hook.
Each rule's own test covers which commands it denies, so the cases here cover only what passes through the hook.
A hook that crashes writes nothing to stdout, which the PreToolUse caller reads as allowing the command, so a failing case prints the hook's stderr.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from hook_testing import report

HOOK = str(Path(__file__).with_name("bash-rules.py"))


def run_hook(stdin):
    """Return (how many reasons the hook gave for denying the command in `stdin`, the hook's stderr)."""
    result = subprocess.run([sys.executable, HOOK], input=stdin, capture_output=True, text=True)
    if not result.stdout.strip():
        return 0, result.stderr
    decision = json.loads(result.stdout)["hookSpecificOutput"]
    if decision["permissionDecision"] != "deny":
        return 0, result.stderr
    return len(decision["permissionDecisionReason"].splitlines()), result.stderr


def hook_input(command, cwd):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)})


def main():
    with tempfile.TemporaryDirectory() as root:
        project = Path(root)
        (project / ".venv").mkdir()
        (project / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin\n")
        # Each case is (hook input, how many rules the command breaks).
        cases = [
            (hook_input("ls src", project), 0),
            (hook_input("grep -n TODO src/main.py", project), 1),
            (hook_input("cd src", project), 1),
            # A command breaking several rules gets every rule's reason.
            (hook_input("cd src && grep -n TODO main.py", project), 2),
            # The venv rule reads `cwd` from the hook input.
            (hook_input("python3 x.py", project), 1),
            (hook_input("python3 x.py", project.parent), 0),
            # Input that is not a JSON object allows the command.
            ("not json", 0),
        ]
        failures = 0
        for stdin, broken in cases:
            reasons, stderr = run_hook(stdin)
            if reasons == broken:
                continue
            failures += 1
            print(f"FAIL want {broken} reasons, got {reasons}: {stdin}")
            if stderr.strip():
                print(f"    {stderr.strip().splitlines()[-1]}")
    report(failures, len(cases))


if __name__ == "__main__":
    main()
