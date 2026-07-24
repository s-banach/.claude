#!/usr/bin/env python3
"""Check no-unscoped-search.py against commands whose verdict is known.

Run `python3 no-unscoped-search-test.py` from this directory after editing the hook.
Each case is (command, denied), where denied is True when the hook must block it.
"""

import json
import subprocess
import sys
from pathlib import Path

HOOK = str(Path(__file__).with_name("no-unscoped-search.py"))

CASES = [
    # Recursive search with no scope: denied.
    ("grep -r TODO .", True),
    ("grep -rn TODO", True),
    ("grep -R pattern /", True),
    ("grep --recursive pattern ~", True),
    ("rg TODO", True),
    ("rg TODO .", True),
    ("ag pattern", True),
    ("sudo grep -r secret /", True),
    ("cd /tmp && grep -r x .", True),
    # Recursive search rooted in a dependency or build directory: denied.
    ("grep -r pattern .venv", True),
    ("rg pattern node_modules", True),
    ("rg pattern crate/target/debug", True),
    ("find node_modules -name '*.json'", True),
    # Ignore rules switched off: denied.
    ("rg -uu pattern src/", True),
    ("rg --no-ignore pattern src/", True),
    # Unbounded walk: denied.
    ("find . -name '*.rs'", True),
    ("find", True),
    ("find / -name x", True),
    ("fd -e rs", True),
    # Scoped search: allowed.
    ("grep -r TODO crate/src", False),
    ("rg TODO crate/src", False),
    ("rg -t rust TODO crate/src", False),
    ("find crate/src -name '*.rs'", False),
    ("find . -maxdepth 1 -name '*.toml'", False),
    # Not a recursive walk: allowed.
    ("grep -c . settings.json", False),
    ("grep -n TODO crate/src/engine.rs", False),
    ("git diff -W crate/src/engine.rs | grep -v '^[+-]'", False),
    ("cargo test 2>&1 | grep -c FAILED", False),
    ("pmset -g assertions | grep caffeinate", False),
    ("git grep engine", False),
    ("grep -e pattern Cargo.toml", False),
    # Redirections are not search paths.
    ("grep -rn pattern crate/src 2>/dev/null", False),
    ("rg pattern crate/src > .venv/out.txt", False),
    ("grep -rn pattern crate/src 2> log.txt", False),
    # Untouched commands.
    ("ls -la", False),
    ("cat notes.txt", False),
    ("./scripts/lint.sh", False),
    ("echo 'the word grep in a string'", False),
    ('python3 -c "s = \\"a | grep -r b\\"; print(s)"', False),
]


def verdict(command):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    result = subprocess.run(
        [sys.executable, HOOK], input=payload, capture_output=True, text=True
    )
    return bool(result.stdout.strip())


def main():
    failures = 0
    for command, denied in CASES:
        got = verdict(command)
        if got != denied:
            failures += 1
            want = "DENY" if denied else "allow"
            print(f"FAIL want {want}: {command}")
    print(f"{len(CASES) - failures}/{len(CASES)} cases pass")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
