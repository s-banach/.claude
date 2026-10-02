#!/usr/bin/env python3
"""Check no_interactive_python.py against commands whose verdict is known.

Run `python3 ~/.claude/hooks/no_interactive_python_test.py` after editing the rule.
"""

import no_interactive_python
from hook_testing import check, report

CASES = [
    # Nothing to run: the interactive interpreter starts.
    (".venv/Scripts/python.exe 2>/dev/null;", True),
    ("python", True),
    (".venv/bin/python3 -u", True),
    ("python -X dev", True),
    ("python -i script.py", True),
    ("ls && python", True),
    # A program to run, or an option that prints and exits.
    ("python script.py", False),
    (".venv/bin/python -c 'print(1)'", False),
    ("python -m pytest", False),
    ("python -mpytest", False),
    ("python -X dev script.py", False),
    ("python --version", False),
    ("python -V", False),
    ("python -VV", False),
    ("python --help-all", False),
    ("python -m pip install -i https://example.org/simple pkg", False),
    ("python script.py -i in.txt", False),
    # A program on stdin.
    ("echo 'print(1)' | python", False),
    ("python - <<'EOF'\nprint(1)\nEOF", False),
    ("python <<EOF\nprint(1)\nEOF", False),
    ("python < script.py", False),
    # Not an interpreter.
    ("which python", False),
    ("pythonista", False),
]


def main():
    report(check(no_interactive_python, CASES), len(CASES))


if __name__ == "__main__":
    main()
