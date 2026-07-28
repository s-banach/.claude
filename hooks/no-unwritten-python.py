#!/usr/bin/env python3
"""PreToolUse hook for Bash: deny Python that modifies files without a script file.

Reads the hook input JSON on stdin and writes a PreToolUse decision on stdout.
Code passed inline (`python -c`) or read from stdin (a heredoc, a herestring, a pipe, a `-` argument, a bare interpreter) leaves no file to review, rerun, or diff.
The hook denies such an invocation only when the command also matches WRITE_PATTERN, so inline code that only computes or prints is allowed.
The WRITE_PATTERN scan covers the whole command string, heredoc bodies included.
A script file, a module (`-m`), a version or help query, and `python < file.py` are left alone; a file holds their source.
Stdin fed to a script file is that script's input, not Python source, so `python etl.py <<EOF` is left alone too.
A `uv run` prefix is unwrapped and the interpreter behind it judged by the same rules; which interpreter a command uses is a separate concern this hook does not check.
"""

import json
import re
import sys

# A redirection, with its target attached (`2>log`) or in the next argument (`2> log`).
REDIRECT = re.compile(r"^(?P<fd>\d*|&)(?P<op>>>|>|<<<|<<|<)(?P<target>.*)$")

PYTHON = re.compile(r"^python(\d+(\.\d+)*)?$")

# Python source that modifies files: open() with a write, append, create, or
# update mode, a Path write, truncate, or a shutil/os move, copy, or delete.
# The quote class includes backslash so escaped quotes inside a double-quoted
# shell string still match.
WRITE_PATTERN = re.compile(
    r"\bopen\s*\([^)]*[\\'\"][rbt]*[wax+][rbtwax+]*[\\'\"]"
    r"|\.write_text\s*\("
    r"|\.write_bytes\s*\("
    r"|\.truncate\s*\("
    r"|\bshutil\.(?:copy\w*|move)\s*\("
    r"|\bos\.(?:rename|replace|remove|unlink)\s*\("
    r"|\.unlink\s*\("
)

# Flags that print and exit, so a command with no script is not reading stdin.
PRINT_AND_EXIT_FLAGS = {"-V", "-VV", "--version", "-h", "--help"}
# Python options that consume the argument after them.
PYTHON_VALUE_OPTIONS = {"-W", "-X", "--check-hash-based-pycs"}
# `uv run` options that consume the argument after them.
UV_RUN_VALUE_OPTIONS = {
    "--with", "--with-editable", "--with-requirements", "--python", "-p",
    "--group", "--only-group", "--extra", "--package", "--project",
    "--directory", "--env-file", "--index", "--default-index", "--find-links",
}
# Words to skip when locating the head of a segment.
PREFIXES = {
    "sudo", "command", "time", "nice", "nohup", "builtin", "exec", "xargs",
    "then", "do", "else",
}

ALTERNATIVE = (
    "The command matches a file-write pattern. Edit files with the Edit or "
    "Write tool. For a larger job, write the code to a file and run that "
    "file; put a throwaway script in the scratchpad directory with a "
    "'THROWAWAY. NOT FOR PROD USE' header."
)


def split_segments(command):
    """Yield the command's segments, splitting on shell operators outside quotes."""
    segments, buf, quote, i, n = [], [], None, 0, len(command)
    while i < n:
        ch = command[i]
        if quote:
            if ch == "\\" and quote == '"' and i + 1 < n:
                buf.append(command[i : i + 2])
                i += 2
                continue
            if ch == quote:
                quote = None
            buf.append(ch)
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            buf.append(command[i : i + 2])
            i += 2
            continue
        if command[i : i + 2] in ("||", "&&", "|&", "$("):
            segments.append("".join(buf))
            buf, i = [], i + 2
            continue
        if ch in "|;\n&`()":
            segments.append("".join(buf))
            buf, i = [], i + 1
            continue
        buf.append(ch)
        i += 1
    segments.append("".join(buf))
    return segments


def split_words(segment):
    """Split a segment on whitespace outside quotes, keeping quote characters."""
    words, buf, quote, i, n = [], [], None, 0, len(segment)
    while i < n:
        ch = segment[i]
        if quote:
            if ch == "\\" and quote == '"' and i + 1 < n:
                buf.append(segment[i : i + 2])
                i += 2
                continue
            if ch == quote:
                quote = None
            buf.append(ch)
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            buf.append(segment[i : i + 2])
            i += 2
            continue
        if ch.isspace():
            if buf:
                words.append("".join(buf))
                buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if buf:
        words.append("".join(buf))
    return words


def resolve_head(segment):
    """Return (program name, its arguments) for a segment, or (None, [])."""
    words = split_words(segment)
    saw_prefix = False
    while words:
        word = words[0]
        if "=" in word.split("/")[0] and not word.startswith("="):
            words = words[1:]  # leading VAR=value assignment
            continue
        if word in PREFIXES:
            words, saw_prefix = words[1:], True
            continue
        if word.startswith("-") and saw_prefix:
            words = words[1:]  # options belonging to a skipped prefix word
            continue
        break
    if not words:
        return None, []
    return words[0].rsplit("/", 1)[-1], words[1:]


def unwrap_uv_run(head, args):
    """Return the (interpreter, its arguments) behind `uv run`, or (None, []).

    `uv run -m module` runs written code, so it resolves to no interpreter,
    the same as a non-Python command.
    """
    if head != "uv" or not args or args[0] != "run":
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
        return word.rsplit("/", 1)[-1], words[1:]
    return None, []


def python_verdict(head, args):
    """Return the reason this interpreter invocation is denied, or None."""
    source_in_file = False
    skip = False
    for i, arg in enumerate(args):
        if skip:
            skip = False
            continue
        redirect = REDIRECT.match(arg)
        if redirect:
            if redirect.group("op") == "<" and not redirect.group("fd"):
                source_in_file = True  # `python < file.py`: a file holds the source
            skip = not redirect.group("target")
            continue
        if arg == "-c":
            return f"`{head} -c` runs code that was never written to a file."
        if arg == "-":
            return f"`{head} -` reads its program from stdin, so no file holds it."
        if arg in ("-m", "--module") or arg in PRINT_AND_EXIT_FLAGS:
            return None
        if arg in PYTHON_VALUE_OPTIONS:
            skip = True
            continue
        if arg.startswith("-"):
            continue
        return None  # a script file: its stdin, piped or heredoc, is data
    if source_in_file:
        return None
    return (
        f"`{head}` with no script reads its program from stdin (a pipe, a "
        "heredoc, or a REPL), so no file holds it."
    )


def verdict(segment):
    """Return the reason this segment is denied, or None."""
    head, args = resolve_head(segment)
    if head is None:
        return None
    if not PYTHON.match(head):
        head, args = unwrap_uv_run(head, args)
        if head is None or not PYTHON.match(head):
            return None
    return python_verdict(head, args)


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not WRITE_PATTERN.search(command):
        sys.exit(0)
    for segment in split_segments(command):
        reason = verdict(segment)
        if reason:
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": f"{reason} {ALTERNATIVE}",
                        }
                    }
                )
            )
            sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
