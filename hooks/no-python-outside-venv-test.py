#!/usr/bin/env python3
"""Check no-python-outside-venv.py against commands whose verdict is known.

Run `python3 no-python-outside-venv-test.py` from this directory after editing the hook.
Each case is (command, denied), where denied is True when the hook must block it
in a directory that holds a `.venv`. Every case is also run in a directory that
holds none, where the hook must allow it.
"""

import tempfile
from pathlib import Path

from hook_testing import check, report

HOOK = str(Path(__file__).with_name("no-python-outside-venv.py"))

CASES = [
    # A bare interpreter name resolves through PATH: denied.
    ("python script.py", True),
    ("python3 script.py", True),
    ("python3.12 -c 'print(1)'", True),
    ("python", True),
    ("sudo python3 script.py", True),
    ("env python3 script.py", True),
    ("cd src && python3 -m pytest", True),
    ("cat data.json | python3 process.py", True),
    ("PYTHONPATH=. python3 script.py", True),
    # An interpreter named by path, or chosen by uv: allowed.
    (".venv/bin/python script.py", False),
    ("/Users/me/proj/.venv/bin/python3 script.py", False),
    ("uv run script.py", False),
    ("uv run python script.py", False),
    ("uv run -m pkg.runner", False),
    ("uvx ruff check src/", False),
    # Commands that only name an interpreter: allowed.
    ("which python", False),
    ("command -v python3", False),
    ("command -V python", False),
    ("command -pv python3", False),
    ("command -p -v python3", False),
    # `command -p` with no -v really does run the interpreter.
    ("command -p python3 script.py", True),
    ("echo 'run python3 by hand'", False),
    ("ls python", False),
    ("git commit -m 'switch to python3'", False),
]


def main():
    with tempfile.TemporaryDirectory() as root:
        with_venv = Path(root) / "with-venv" / "src"
        without_venv = Path(root) / "without-venv" / "src"
        with_venv.mkdir(parents=True)
        without_venv.mkdir(parents=True)
        venv = with_venv.parent / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("home = /usr/bin\n")

        failures = check(HOOK, CASES, cwd=with_venv, note=" beside a .venv")
        failures += check(
            HOOK,
            [(command, False) for command, _ in CASES],
            cwd=without_venv,
            note=" with no .venv",
        )
    report(failures, len(CASES) * 2)


if __name__ == "__main__":
    main()
