#!/usr/bin/env python3
"""Check no-unscoped-search.py against commands whose verdict is known.

Run `python3 no-unscoped-search-test.py` from this directory after editing the hook.
Each case is (command, denied), where denied is True when the hook must block it.
"""

from pathlib import Path

from hook_testing import check, report

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
    # A quoted root is still that root.
    ('grep -r pattern "."', True),
    ("grep -r pattern '.'", True),
    ('grep -r pattern "$HOME"', True),
    # Recursive search rooted in a dependency or build directory: denied.
    ("grep -r pattern .venv", True),
    ("rg pattern node_modules", True),
    ("rg pattern crate/target/debug", True),
    ("find node_modules -name '*.json'", True),
    ('rg pattern "node_modules"', True),
    ('grep -r TODO "my dir/node_modules"', True),
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
    ("rg --max-depth 1 pattern .", False),
    ("rg --max-depth=1 pattern .", False),
    ('grep -r TODO "crate/src"', False),
    ('grep -r TODO "my dir"', False),
    # An option's value is not a search path.
    ("find src -name node_modules", False),
    ("find crate/src -name .venv", False),
    ("grep -r pattern src --exclude-dir node_modules", False),
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
    # `command -v` prints where a program lives and runs nothing.
    ("command -v rg", False),
    ("command -V grep", False),
    ("command -p rg pattern .", True),
    ("command rg -v pattern .", True),
]


def main():
    report(check(HOOK, CASES), len(CASES))


if __name__ == "__main__":
    main()
