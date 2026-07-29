#!/usr/bin/env python3
"""PreToolUse hook for Bash: deny a file-modifying program that no file holds.

Reads the hook input JSON on stdin and writes a PreToolUse decision on stdout.
A program passed on the command line (`python -c`, `perl -e`), read from stdin (a heredoc, a herestring, a pipe, a `-` argument, a bare interpreter), or handed to a stream editor as a positional (`sed -i`) leaves no file to read, review, rerun, or diff.
Which language the program is written in does not change that, so INTERPRETERS is a table; a language added there also needs its file-modifying calls added to WRITE_PATTERN, or the hook cannot see that it writes.
An interpreter is denied only when the command also modifies files, which is true when WRITE_PATTERN matches or the invocation carries an in-place flag; a program that only computes or prints is left alone.
The WRITE_PATTERN scan covers the whole command string, heredoc bodies included, because splitting a command into segments splits a heredoc body away from the interpreter that reads it.
A script file, a module (`python -m`), a `-f` program file, a version or help query, and `python < file.py` are left alone; a file holds their program.
Stdin fed to a script file is that script's input, not program text, so `python etl.py <<EOF` is left alone too.
A `uv run` prefix is unwrapped and the interpreter behind it judged by the same rules; whether a command should use `uv` is checked by no-python-outside-venv.py.
"""

import re
from collections import namedtuple

from shell_parsing import (
    base_name,
    deny,
    iter_arguments,
    program_name,
    read_input,
    redirects_stdin_from_file,
    resolve_head,
    split_segments,
)

# Program text that modifies files. The quote class includes backslash so
# escaped quotes inside a double-quoted shell string still match.
WRITE_PATTERN = re.compile(
    # Python and Ruby: open() in a write, append, create, or update mode.
    r"\bopen\s*\([^)]*[\\'\"][rbt]*[wax+][rbtwax+]*[\\'\"]"
    # Perl: open() with a shell-style write or append mode.
    r"|\bopen\s*\([^)]*[\\'\"]\s*>>?"
    # Python pathlib and shutil and os.
    r"|\.write_text\s*\("
    r"|\.write_bytes\s*\("
    r"|\.truncate\s*\("
    r"|\bshutil\.(?:copy\w*|move)\s*\("
    r"|\bos\.(?:rename|replace|remove|unlink)\s*\("
    r"|\.unlink\s*\("
    # Ruby.
    r"|\bFile\.(?:write|delete|rename|unlink)\s*\("
    # Node.
    r"|\bfs\.(?:writeFile|appendFile|copyFile|rename|unlink|rm|rmdir|truncate"
    r"|createWriteStream)\w*\s*\("
    r"|\b(?:writeFile|appendFile|copyFile)Sync\s*\("
)

# For each interpreter: the short option letters that introduce program text,
# the long flags that do, the letters whose value names an installed module
# that holds the program, the letters whose value is attached to them (so a
# scan of a bundled cluster stops there rather than reading the value as more
# option letters), the flags whose value is the next argument, and whether `-i`
# makes the interpreter rewrite the file it reads.
Interpreter = namedtuple(
    "Interpreter",
    "inline_letters inline_flags module_letters value_letters value_flags rewrites_in_place",
)

INTERPRETERS = {
    "python": Interpreter(
        inline_letters=set("c"),
        inline_flags=set(),
        module_letters=set("m"),
        value_letters=set("WX"),
        value_flags={"-W", "-X", "--check-hash-based-pycs"},
        rewrites_in_place=False,
    ),
    # `-M` and `-m` preload a module; the program still comes from elsewhere.
    "perl": Interpreter(
        inline_letters=set("eE"),
        inline_flags=set(),
        module_letters=set(),
        value_letters=set("MmIFDxCS"),
        value_flags={"-I", "-M", "-m", "-F", "-D"},
        rewrites_in_place=True,
    ),
    "ruby": Interpreter(
        inline_letters=set("e"),
        inline_flags=set(),
        module_letters=set(),
        value_letters=set("IrKCEFTWx"),
        value_flags={"-I", "-r", "-C", "-E", "-F", "-K", "-T", "-W"},
        rewrites_in_place=True,
    ),
    "node": Interpreter(
        inline_letters=set("ep"),
        inline_flags={"--eval", "--print"},
        module_letters=set(),
        value_letters=set("r"),
        value_flags={"-r", "--require", "--input-type"},
        rewrites_in_place=False,
    ),
}

# Their program is a positional argument, so only `-f` puts it in a file, and
# an in-place flag is what makes them write rather than print.
STREAM_EDITORS = {"sed", "awk", "gawk", "nawk", "mawk"}
PROGRAM_FILE_FLAGS = {"-f", "--file"}

# Their program arrives on stdin or in a `-c` argument and their purpose is to
# rewrite the file they open, so no invocation of them holds its program in a file.
LINE_EDITORS = {"ed", "ex"}

# Flags that print and exit, so a command with no script is not reading stdin.
PRINT_AND_EXIT_FLAGS = {"-V", "-VV", "--version", "-h", "--help"}
# `uv run` options that consume the argument after them.
UV_RUN_VALUE_OPTIONS = {
    "--with", "--with-editable", "--with-requirements", "--python", "-p",
    "--group", "--only-group", "--extra", "--package", "--project",
    "--directory", "--env-file", "--index", "--default-index", "--find-links",
}

ALTERNATIVE = (
    "Edit files with the Edit or Write tool. For a change across many files: "
    "write the program to a file, read that file back and confirm it is correct "
    "for every file it will change, then run it. Put a throwaway script in the "
    "scratchpad directory with a 'THROWAWAY. NOT FOR PROD USE' header."
)


def scan_cluster(cluster, spec):
    """Return what the first meaningful letter of a bundled short-option cluster is.

    One of "program", "module", "in_place", or None. Walks the letters left to
    right and stops at the first one whose value is attached, so
    `-MTime::HiRes` is not read as containing perl's `-i`.
    """
    for ch in cluster:
        if not ch.isalpha():
            return None  # a digit or punctuation starts an attached value
        if ch in spec.inline_letters:
            return "program"
        if ch in spec.module_letters:
            return "module"
        if ch == "i" and spec.rewrites_in_place:
            return "in_place"
        if ch in spec.value_letters:
            return None
    return None


def unwrap_uv_run(word, args):
    """Return the (interpreter, its arguments) behind `uv run`, or (None, []).

    `uv run -m module` runs written code, so it resolves to no interpreter,
    the same as a non-Python command.
    """
    if program_name(word) != "uv" or not args or args[0] != "run":
        return None, []
    words = args[1:]
    while words:
        word = words[0]
        if word in ("-m", "--module"):
            return None, []
        if word in UV_RUN_VALUE_OPTIONS:
            words = words[2:]
            continue
        if word.startswith("-"):
            words = words[1:]
            continue
        return word, words[1:]
    return None, []


def interpreter_verdict(name, args, writes):
    """Return the reason this interpreter invocation is denied, or None."""
    spec = INTERPRETERS[name]
    inline_flag = None
    reads_stdin = False
    in_place = False
    for arg in iter_arguments(args, spec.value_flags):
        if arg in spec.inline_flags:
            inline_flag = arg
            break
        if arg in PRINT_AND_EXIT_FLAGS:
            return None
        if arg == "-":
            reads_stdin = True
            break
        if arg.startswith("-"):
            meaning = scan_cluster(arg[1:], spec)
            if meaning == "module":
                return None  # an installed module holds the program
            if meaning == "program":
                inline_flag = arg
                break
            if meaning == "in_place":
                in_place = True
            continue
        return None  # a script file: its stdin, piped or heredoc, is data
    if not (writes or in_place):
        return None
    if inline_flag:
        return f"`{name} {inline_flag}` runs a program that no file holds."
    if redirects_stdin_from_file(args):
        return None  # `python < file.py`, `python - < file.py`: a file holds the program
    if reads_stdin:
        return f"`{name} -` reads its program from stdin, so no file holds it."
    return (
        f"`{name}` with no script reads its program from stdin (a pipe, a "
        "heredoc, or a REPL), so no file holds it."
    )


def stream_editor_verdict(name, args):
    """Return the reason this stream editor invocation is denied, or None."""
    program_in_file = False
    in_place = False
    for arg in iter_arguments(args, PROGRAM_FILE_FLAGS):
        if arg == "--file" or arg.startswith("-f") or arg.startswith("--file="):
            program_in_file = True
            continue
        if arg == "--in-place" or arg.startswith("--in-place="):
            in_place = True
            continue
        # Only a short cluster, because every long option holding an `i` would
        # otherwise read as in-place: `--version`, `--posix`, `--silent`.
        if arg.startswith("-") and not arg.startswith("--"):
            in_place = in_place or "i" in arg[1:].split(".")[0]
    if in_place and not program_in_file:
        return f"`{name}` rewrites a file with a program that no file holds."
    return None


def verdict(segment, writes):
    """Return the reason this segment is denied, or None."""
    word, args = resolve_head(segment)
    if word is None:
        return None
    name = base_name(word)
    if name in LINE_EDITORS:
        return f"`{name}` edits a file with a program that no file holds."
    if name in STREAM_EDITORS:
        return stream_editor_verdict(name, args)
    if name not in INTERPRETERS:
        word, args = unwrap_uv_run(word, args)
        if word is None:
            return None
        name = base_name(word)
        if name not in INTERPRETERS:
            return None
    return interpreter_verdict(name, args, writes)


def main():
    command, _ = read_input()
    writes = bool(WRITE_PATTERN.search(command))
    for segment in split_segments(command):
        reason = verdict(segment, writes)
        if reason:
            deny(f"{reason} {ALTERNATIVE}")


if __name__ == "__main__":
    main()
