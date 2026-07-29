#!/usr/bin/env python3
"""PreToolUse hook for Bash: deny a bare `python` when the project has a virtualenv.

Reads the hook input JSON on stdin and writes a PreToolUse decision on stdout.
A bare `python` or `python3` runs whichever interpreter PATH resolves first, so
in a project holding a `.venv` it usually runs the system interpreter: imports
resolve to a different set of packages than the project installed, and the run
produces wrong results with no error.
An interpreter named by path (`.venv/bin/python`) and a `uv run` prefix are left
alone; both say which environment they run in.
Whether a program should run from a file at all is checked by
no-scriptless-file-writes.py.
"""

import os
from pathlib import Path

from shell_parsing import base_name, deny, read_input, resolve_head, split_segments


def find_venv(start):
    """Return the nearest `.venv` at or above `start`, or None."""
    for directory in (start, *start.parents):
        candidate = directory / ".venv"
        if (candidate / "pyvenv.cfg").exists():
            return candidate
    return None


def verdict(segment):
    """Return the name of the bare interpreter this segment runs, or None."""
    word, _ = resolve_head(segment)
    if word is None or "/" in word:
        return None  # a path says which environment it runs in
    return word if base_name(word) == "python" else None


def main():
    command, payload = read_input()
    for segment in split_segments(command):
        name = verdict(segment)
        if not name:
            continue
        venv = find_venv(Path(payload.get("cwd") or os.getcwd()).resolve())
        if venv is None:
            return
        deny(
            f"`{name}` runs whichever interpreter PATH resolves first, and this "
            f"project has a virtualenv at `{venv}`. Run `uv run <script>`, or "
            f"name the interpreter `{venv}/bin/python`."
        )


if __name__ == "__main__":
    main()
