"""Rule for `bash-rules.py`: deny a bare `python` that runs a project's code with an interpreter outside the project's virtualenv.

A bare `python` or `python3` runs whichever interpreter PATH resolves first.
When that interpreter is outside the `.venv` of the project whose code it runs, imports resolve to a different set of packages than the project installed, and the run produces wrong results with no error.
The project is the one holding the script, or the one holding `cwd` for `-c` code, a `-m` module, or a program on stdin, since `sys.path` starts with that directory for them, unless `-P` or `-I` is given.
The rule allows an interpreter named by path (`.venv/bin/python`), a `uv run` prefix, a PATH that resolves into the project's `.venv` (an activated virtualenv), an option that prints and exits (`--version`), `-m venv`, which creates a virtualenv and so needs an interpreter from outside one, and a name PATH does not resolve, which fails with an error.
The PATH it resolves with is this hook's own, which matches the PATH a command starts with in the shell Claude Code runs it in; a command that changes PATH before the interpreter runs (`source .venv/bin/activate && python3 x.py`, `PATH=.venv/bin:$PATH python3 x.py`) is judged by the PATH it starts with.
"""

import os
import shutil
from itertools import chain
from pathlib import Path

from shell_parsing import base_name, iter_arguments, resolve_head

# Short options whose value is the rest of their argument, or the next argument when nothing follows the letter (`-Bc code`, `-Wignore`, `-mvenv`).
SHORT_VALUE_OPTIONS = "cmWX"

# Options whose value is the next argument, once `split_short_options` has split each group of short options.
VALUE_OPTIONS = ("-X", "-W", "--check-hash-based-pycs")

# Options that print and exit, running no code.
PRINTS_AND_EXITS = {"-V", "--version", "-h", "-?", "--help", "--help-env", "--help-xoptions", "--help-all"}


def find_venv(start):
    """Return the nearest `.venv` at or above `start`, or None."""
    for directory in (start, *start.parents):
        candidate = directory / ".venv"
        if (candidate / "pyvenv.cfg").exists():
            return candidate
    return None


def script_directory(word, cwd):
    """Return the directory holding the script `word` names, taking a relative name from `cwd`."""
    return (cwd / os.path.expandvars(os.path.expanduser(word))).resolve().parent


def split_short_options(arg):
    """Return a group of short options as one argument per option, with an attached value as an argument of its own (`-Bc` -> `-B -c`, `-Wignore` -> `-W ignore`), as CPython reads it; return any other argument alone."""
    if not arg.startswith("-") or arg.startswith("--") or arg == "-":
        return [arg]
    letters = arg[1:]
    end = next((index + 1 for index, letter in enumerate(letters) if letter in SHORT_VALUE_OPTIONS), len(letters))
    return [f"-{letter}" for letter in letters[:end]] + ([letters[end:]] if end < len(letters) else [])


def code_directory(args, cwd):
    """Return the directory whose project the interpreter's code comes from, given the interpreter's arguments, or None when it runs no project code.

    That is the script's directory, or `cwd` for `-c` code, a `-m` module, or a program on stdin (`-`, or no program at all).
    None means an option in `PRINTS_AND_EXITS`, or `-m venv`.
    """
    arguments = iter_arguments(chain.from_iterable(map(split_short_options, args)), VALUE_OPTIONS)
    for arg in arguments:
        if arg in PRINTS_AND_EXITS:
            return None
        if arg == "-m":
            return None if next(arguments, "") == "venv" else cwd
        if arg in ("-c", "-"):
            return cwd
        if not arg.startswith("-"):
            return script_directory(arg, cwd)
    return cwd


def outside_venv(segment, cwd, path):
    """Return the reason this segment runs a project's code with an interpreter outside the project's `.venv`, or None."""
    word, args = resolve_head(segment.text)
    if word is None or "/" in word or base_name(word) != "python":
        return None  # not an interpreter, or one named by path, which says which environment it runs in
    directory = code_directory(args, cwd)
    venv = None if directory is None else find_venv(directory)
    if venv is None:
        return None
    found = shutil.which(word, path=path)
    if found is None or Path(found).parent.resolve().is_relative_to(venv.resolve()):
        return None  # a name PATH does not resolve fails with an error, or the interpreter is the project's
    return (
        f"`{word}` resolves to `{found}`, outside `{venv}`, the virtualenv of the project whose code it runs. "
        f"Run `uv run <script>`, or name the interpreter inside `{venv}` (`bin/python`, or `Scripts/python.exe` on Windows)."
    )


def verdict(segments, cwd, path=None):
    """Return the reason the command, starting in `cwd`, is denied, or None.

    `path` is the PATH that resolves an interpreter's name; None means this process's PATH.
    """
    return next(filter(None, (outside_venv(segment, cwd, path) for segment in segments)), None)
