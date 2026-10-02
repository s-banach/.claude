"""Rule for `bash-rules.py`: deny a Python interpreter that the command gives nothing to run.

Given no script, `-c`, or `-m`, Python reads its program from stdin, and runs the interactive interpreter when stdin looks like a terminal.
On Windows, `.venv/Scripts/python.exe 2>/dev/null` stalled this way with no output, because Python writes the `>>>` prompt to stderr.
`-i` starts the interactive interpreter after the program ends, so it is denied too.
A command that feeds the interpreter a program on stdin, through a pipe, a heredoc, a here-string, or a `<` redirect, is left alone.
"""

from itertools import takewhile

from shell_parsing import REDIRECT, base_name, iter_arguments, resolve_head, split_words

# Options that print and exit.
RUNS_AND_EXITS = {"-V", "-VV", "--version", "-h", "-?", "--help", "--help-env", "--help-xoptions", "--help-all"}

# Options whose value is the next argument.
VALUE_FLAGS = ("-X", "-W")


def reads_program_from_stdin(segment):
    """True when a pipe, heredoc, here-string, or `<` redirect gives this segment's stdin."""
    redirects = filter(None, map(REDIRECT.match, split_words(segment.text)))
    return segment.reads_pipe or any(r.group("fd") in ("", "0") and r.group("op").startswith("<") for r in redirects)


def runs_something(arg):
    """True when this argument makes the interpreter run a program or exit: a script path, `-` for stdin, `-c` or `-m` with or without its value attached, or an option in `RUNS_AND_EXITS`."""
    return not arg.startswith("-") or arg == "-" or arg in RUNS_AND_EXITS or arg[:2] in ("-c", "-m")


def interactive_interpreter(segment):
    """Return the interpreter word this segment starts interactively, or None."""
    word, args = resolve_head(segment.text)
    if word is None or base_name(word) != "python" or reads_program_from_stdin(segment):
        return None
    arguments = list(iter_arguments(args, VALUE_FLAGS))
    # Python passes every argument after the script, `-c`, or `-m` to the program it runs.
    options = list(takewhile(lambda arg: not runs_something(arg), arguments))
    if len(options) == len(arguments) or "-i" in options:
        return word
    return None


def verdict(segments, cwd):
    """Return the reason the command is denied, or None."""
    word = next(filter(None, map(interactive_interpreter, segments)), None)
    if word is None:
        return None
    return (
        f"`{word}` here is given no program to run, so it reads one from stdin, where it can wait forever. "
        "Give it a script, `-c '<code>'`, `-m <module>`, or `--version`, without `-i`."
    )
