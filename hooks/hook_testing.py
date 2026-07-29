#!/usr/bin/env python3
"""Running a hook against commands whose verdict is known, shared by the tests here.

A hook that crashes writes nothing to stdout, which the PreToolUse caller reads
as allowing the command, so `check` prints stderr for a failing case rather than
leaving a crash looking like a verdict.
"""

import json
import subprocess
import sys


def denies(hook_path, command, cwd=None):
    """Return (whether the hook blocked this command, the hook's stderr)."""
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    if cwd is not None:
        payload["cwd"] = str(cwd)
    result = subprocess.run(
        [sys.executable, hook_path],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip()), result.stderr


def check(hook_path, cases, cwd=None, note=""):
    """Print a line for each case the hook gets wrong; return how many there were."""
    failures = 0
    for command, denied in cases:
        blocked, stderr = denies(hook_path, command, cwd)
        if blocked == denied:
            continue
        failures += 1
        want = "DENY" if denied else "allow"
        print(f"FAIL want {want}{note}: {command}")
        if stderr.strip():
            print(f"    {stderr.strip().splitlines()[-1]}")
    return failures


def report(failures, total):
    """Print the pass count and exit non-zero when any case failed."""
    print(f"{total - failures}/{total} cases pass")
    sys.exit(1 if failures else 0)
