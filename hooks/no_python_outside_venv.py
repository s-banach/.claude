"""Rule for `bash-rules.py`: deny a bare `python` when the project has a virtualenv.

A bare `python` or `python3` runs whichever interpreter PATH resolves first, so
in a project holding a `.venv` it usually runs the system interpreter: imports
resolve to a different set of packages than the project installed, and the run
produces wrong results with no error.
An interpreter named by path (`.venv/bin/python`) and a `uv run` prefix are left
alone; both say which environment they run in.
"""

from shell_parsing import base_name, resolve_head


def find_venv(start):
    """Return the nearest `.venv` at or above `start`, or None."""
    for directory in (start, *start.parents):
        candidate = directory / ".venv"
        if (candidate / "pyvenv.cfg").exists():
            return candidate
    return None


def bare_interpreter(segment):
    """Return the name of the bare interpreter this segment runs, or None."""
    word, _ = resolve_head(segment.text)
    if word is None or "/" in word:
        return None  # a path says which environment it runs in
    return word if base_name(word) == "python" else None


def verdict(segments, cwd):
    """Return the reason the command, starting in `cwd`, is denied, or None."""
    name = next(filter(None, map(bare_interpreter, segments)), None)
    if name is None:
        return None
    venv = find_venv(cwd)
    if venv is None:
        return None
    return (
        f"`{name}` runs whichever interpreter PATH resolves first, and this "
        f"project has a virtualenv at `{venv}`. Run `uv run <script>`, or "
        f"name the interpreter `{venv}/bin/python`."
    )
