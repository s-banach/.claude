#!/usr/bin/env python3
"""Check no-unwritten-python.py against commands whose verdict is known.

Run `python3 no-unwritten-python-test.py` from this directory after editing the hook.
Each case is (command, denied), where denied is True when the hook must block it.
"""

import json
import subprocess
import sys
from pathlib import Path

HOOK = str(Path(__file__).with_name("no-unwritten-python.py"))

CASES = [
    # Unwritten source that modifies files: denied.
    ("""python -c 'open("log.txt", "w").write("x")'""", True),
    ('''python3 -c "from pathlib import Path; Path('f').write_text('x')"''', True),
    ("""python3 -c 'open("f", "a").write("x")'""", True),
    ("""python3 -c 'open("f", "r+").truncate(0)'""", True),
    ("""python3.12 -c 'Path("f").write_bytes(b"x")'""", True),
    ("""uv run python -c 'import shutil; shutil.move("a", "b")'""", True),
    ("""uv run --with rich python -c 'import os; os.remove("f")'""", True),
    ("""sudo python3 -c 'import os; os.replace("a", "b")'""", True),
    ("""cd /tmp && python -c 'open("f", "w")'""", True),
    ("""/usr/bin/python3 -c 'open("f", "wb").write(b"x")'""", True),
    # Escaped quotes inside a double-quoted shell string.
    ('python3 -c "open(\\"f\\", \\"w\\").write(\\"x\\")"', True),
    # File-modifying program from stdin: denied.
    ("python3 - <<'EOF'\nopen('f', 'w').write('x')\nEOF", True),
    ("python <<EOF\nimport os\nos.rename('a', 'b')\nEOF", True),
    ("uv run python <<EOF\nPath('f').unlink()\nEOF", True),
    ("python3 <<< 'open(\"f\", \"w\")'", True),
    ("echo 'open(\"f\", \"w\").write(\"x\")' | python3", True),
    # Unwritten source that only computes or prints: allowed.
    ("python -c 'print(1)'", False),
    ('python3 -c "import sys; print(sys.path)"', False),
    ("""python3 -c 'import json; print(json.load(open("data.json")))'""", False),
    ("uv run python -c 'import anthropic'", False),
    ("python3 <<< 'print(1)'", False),
    ("echo 'print(1)' | python3", False),
    ("python", False),
    ("python -u", False),
    ("python3 - <<'EOF'\nprint(1)\nEOF", False),
    # A file holds the source: allowed even when the command mentions writes.
    ("python script.py", False),
    ("python migrate.py <<EOF\nopen('f', 'w')\nEOF", False),
    ("python < script.py", False),
    ("python3 -m pytest", False),
    ("uv run python -m pkg.runner", False),
    ("uv run scripts/migrate.py", False),
    # Print-and-exit flags: allowed.
    ("python --version", False),
    ("python3 -V", False),
    # Untouched commands, with and without a write pattern.
    ("echo \"open('f', 'w')\" > snippet.py", False),
    ("pythonista -c 'open(\"f\", \"w\")'", False),
    ("uv run pytest", False),
    ("which python", False),
    ("echo 'python -c is banned'", False),
    ("git log --oneline", False),
    ("grep -c pattern file.py", False),
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
