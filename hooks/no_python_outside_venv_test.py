#!/usr/bin/env python3
"""Check no_python_outside_venv.py against commands whose verdict is known.

Run `python3 ~/.claude/hooks/no_python_outside_venv_test.py` after editing the rule.
Each case in `CASES` is (command, denied), where denied is True when the rule must block it in a project that holds a `.venv`, with a PATH whose interpreters are outside that `.venv`.
Every case is also run with that `.venv` activated, and in a directory with no `.venv`, where the rule must allow it.
"""

import os
import tempfile
from functools import partial
from pathlib import Path

import no_python_outside_venv
from hook_testing import check, report

INTERPRETER_NAMES = ("python", "python3", "python3.12", "python.exe")

CASES = [
    # A bare interpreter name that resolves outside the project's .venv: denied.
    ("python script.py", True),
    ("python3 script.py", True),
    ("python3.12 -c 'print(1)'", True),
    ("python", True),
    ("python.exe script.py", True),
    ("sudo python3 script.py", True),
    ("env python3 script.py", True),
    ("cd src && python3 -m pytest", True),
    ("cat data.json | python3 process.py", True),
    ("PYTHONPATH=. python3 script.py", True),
    ("~/.claude/bin/run-check python3 -m pytest", True),
    ("python3 -X dev script.py", True),
    ("python3 -mpytest", True),
    ("python3 - < script.py", True),
    ("python3 - /tmp/data.csv", True),
    ("python3 -Bc 'print(1)'", True),
    # `command -p` with no -v really does run the interpreter.
    ("command -p python3 script.py", True),
    # An interpreter named by path, or chosen by uv: allowed.
    (".venv/bin/python script.py", False),
    ("/Users/me/proj/.venv/bin/python3 script.py", False),
    ("uv run script.py", False),
    ("uv run python script.py", False),
    ("uv run -m pkg.runner", False),
    ("uvx ruff check src/", False),
    # An interpreter that runs no project code: allowed.
    ("python3 --version", False),
    ("python3 -V", False),
    ("python3 -VV", False),
    ("python3 --help", False),
    ("python3 -m venv .venv", False),
    ("python3 -mvenv .venv", False),
    ("python3 -Im venv .venv", False),
    ("python3 -IV", False),
    # A name PATH does not resolve fails with an error: allowed.
    ("python2 script.py", False),
    # Commands that only name an interpreter: allowed.
    ("which python", False),
    ("command -v python3", False),
    ("command -V python", False),
    ("command -pv python3", False),
    ("command -p -v python3", False),
    ("echo 'run python3 by hand'", False),
    ("ls python", False),
    ("git commit -m 'switch to python3'", False),
]


def make_interpreters(directory):
    """Create an executable file for each name in `INTERPRETER_NAMES` in `directory`."""
    directory.mkdir(parents=True)
    for name in INTERPRETER_NAMES:
        (directory / name).touch(mode=0o755)


def main():
    with tempfile.TemporaryDirectory() as root:
        root = Path(root).resolve()
        project = root / "project"
        src = project / "src"
        elsewhere = root / "elsewhere"
        src.mkdir(parents=True)
        elsewhere.mkdir()
        venv = project / ".venv"
        make_interpreters(venv / "bin")
        (venv / "pyvenv.cfg").write_text("home = /usr/bin\n")
        system = root / "system-bin"
        make_interpreters(system)

        outside = partial(no_python_outside_venv.verdict, path=str(system))
        activated = partial(no_python_outside_venv.verdict, path=os.pathsep.join([str(venv / "bin"), str(system)]))
        allowed = [(command, False) for command, _ in CASES]
        # The script's location picks the project, whichever directory the command starts in.
        located = [
            (f"python3 {elsewhere}/tool.py", False),
            (f"python3 {src}/tool.py", True),
            (f"python3 {src}/../../elsewhere/tool.py", False),
            (f"python3 {elsewhere}/$(echo tool.py)", False),
            (f"python3 -X dev {elsewhere}/tool.py", False),
            (f"python3 -BW ignore {elsewhere}/tool.py", False),
            (f"python3 --check-hash-based-pycs never {elsewhere}/tool.py", False),
        ]
        # A `.venv` that is a symbolic link, activated through the link.
        linked = root / "linked"
        (linked / "src").mkdir(parents=True)
        (linked / ".venv").symlink_to(venv)
        activated_linked = partial(no_python_outside_venv.verdict, path=os.pathsep.join([str(linked / ".venv" / "bin"), str(system)]))

        failures = check(outside, CASES, cwd=src, note=" in a project with a .venv")
        failures += check(activated, allowed, cwd=src, note=" with the .venv activated")
        failures += check(outside, allowed, cwd=elsewhere, note=" with no .venv")
        failures += check(outside, located, cwd=src, note=" starting in the project")
        failures += check(outside, located, cwd=elsewhere, note=" starting outside the project")
        failures += check(activated_linked, [("python3 script.py", False)], cwd=linked / "src", note=" with a symlinked .venv activated")
    report(failures, len(CASES) * 3 + len(located) * 2 + 1)


if __name__ == "__main__":
    main()
