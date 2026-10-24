#!/usr/bin/env python3
"""Reading a Bash command, and answering the PreToolUse caller, shared by `bash-rules.py` and its rules.

Each rule decides what a command means.
This module decides where the command's parts begin and end, and how a decision reaches the PreToolUse caller.
A rule imports it by name because Python puts the running script's directory first on `sys.path`.
"""

import json
import os
import re
import shlex
import sys
from functools import partial, reduce
from pathlib import Path
from typing import NamedTuple

# A redirection, with its target attached (`2>log`) or in the next argument (`2> log`).
REDIRECT = re.compile(r"^(?P<fd>\d*|&)(?P<op>>>|>|<<<|<<-|<<|<)(?P<target>.*)$")

# A heredoc operator and the word naming the line that ends its body (`<<EOF`, `<<-'EOF'`, `<< "EOF"`).
HEREDOC = re.compile(r"<<(?P<dash>-?)[ \t]*(?P<word>(?:'[^']*'|\"[^\"]*\"|\\.|[^\s;|&()<>'\"\\])+)")

# A quoted or backslash-escaped piece of a heredoc word; the group that matched holds the text it stands for.
QUOTED_PIECE = re.compile(r"'([^']*)'|\"([^\"]*)\"|\\(.)")

# An arithmetic expansion (`$((n+1))`) with no command substitution inside, which runs no command; one level of parentheses may nest inside it.
ARITHMETIC = re.compile(r"\$\(\((?:[^()$]|\$(?!\()|\((?:[^()$]|\$(?!\())*\))*\)\)")


class Prefix(NamedTuple):
    """A program or keyword that runs the command written after it: its options that take the next word as their value, and how many operands come before that command."""

    value_options: frozenset = frozenset()
    operands: int = 0


# Programs and keywords to skip when locating the head of a segment, whatever directory the word names them from.
PREFIXES = {
    "sudo": Prefix(
        frozenset({
            "-a", "-c", "-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U", "-T", "-R",
            "--user", "--group", "--close-from", "--chdir", "--host", "--prompt", "--role", "--type",
            "--other-user", "--command-timeout", "--chroot",
        })
    ),
    "env": Prefix(frozenset({"-u", "-C", "-P", "-S", "--unset", "--chdir", "--split-string"})),
    "nice": Prefix(frozenset({"-n", "--adjustment"})),
    "exec": Prefix(frozenset({"-a"})),
    "xargs": Prefix(
        frozenset({
            "-E", "-I", "-J", "-L", "-n", "-P", "-R", "-S", "-s", "-a", "-d",
            "--max-args", "--max-procs", "--max-chars", "--arg-file", "--delimiter",
        })
    ),
    "timeout": Prefix(frozenset({"-s", "-k", "--signal", "--kill-after"}), operands=1),
    **dict.fromkeys(
        ("command", "time", "nohup", "builtin", "run-check", "if", "elif", "while", "until", "then", "do", "else", "!", "{"),
        Prefix(),
    ),
}

# Shells that run the command string given with `-c`.
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}

# Letters of shell options whose value is the next word, one word for each such letter in a group (`-euo pipefail`).
SHELL_VALUE_LETTERS = "oO"


# The word that stands in for a command substitution in the command around it, since the hook cannot know what the substitution prints. It is a plain word, so a command string that holds it (`sh -c "git commit -m $(cat msg)"`) reads it as an argument.
SUBSTITUTION = "substitution-output"


class Segment(NamedTuple):
    """One command between shell operators, and whether it runs inside a command substitution."""

    text: str
    inside_substitution: bool


class OpenSubstitution(NamedTuple):
    """The segment a command substitution interrupted, resumed when `closer` ends the substitution, inside the quote that was open when it began (`"` or None)."""

    buf: list
    closer: str
    open_parens: int
    quote: str | None


class Heredoc(NamedTuple):
    """A heredoc whose body starts on the next line: the line that ends the body, and whether `<<-` strips leading tabs before comparing a line to it."""

    delimiter: str
    strips_tabs: bool


def end_of_heredoc_body(command, start, heredoc):
    """Return the index just past the line that ends this heredoc's body, which begins at `start`, or None when `start` is None or no line ends the body."""
    if start is None:
        return None
    tabs = "\t*" if heredoc.strips_tabs else ""
    end = re.compile(rf"^{tabs}{re.escape(heredoc.delimiter)}$\n?", re.MULTILINE).search(command, start)
    return end.end() if end else None


def end_of_heredoc_bodies(command, newline, heredocs):
    """Return the index just past the bodies of `heredocs`, which follow one another from the newline at `newline`, or None when `heredocs` is empty or a body has no end line."""
    if not heredocs:
        return None
    return reduce(partial(end_of_heredoc_body, command), heredocs, newline + 1)


def split_segments(command):
    """Return the commands that `command` runs, each as a `Segment`.

    These are the parts `split_operators` finds, with a command that runs a command string as shell code (`sh -c '...'`, `eval '...'`) replaced by the segments of that string.
    """
    return [nested for segment in split_operators(command) for nested in run_segments(segment)]


def run_segments(segment):
    """Return the segments of the command string `segment` runs as shell code, or `segment` itself when it runs none."""
    script = command_string(*resolve_head(segment.text))
    if script is None:
        return [segment]
    return [Segment(nested.text, nested.inside_substitution or segment.inside_substitution) for nested in split_segments(script)]


def command_string(word, args):
    """Return the command string that the command word and arguments run as shell code, or None.

    That is the joined arguments of `eval`, or the first operand of a shell in `SHELLS` given `-c`, alone or grouped with other options (`-lc`).
    """
    if word is None:
        return None
    name = program_name(word)
    if name == "eval":
        return " ".join(args)
    if name not in SHELLS:
        return None
    arguments = list(iter_arguments(args))
    index, letters = 0, ""
    while index < len(arguments) and arguments[index][:1] in ("-", "+") and arguments[index] not in ("-", "+"):
        option = arguments[index]
        index += 1
        if option == "--":
            break
        if not option.startswith("--"):
            letters += option[1:] if option[0] == "-" else ""
            index += sum(letter in SHELL_VALUE_LETTERS for letter in option[1:])
    operands = arguments[index:]
    return operands[0] if "c" in letters and operands else None


def split_operators(command):
    """Return the command's segments, splitting on shell operators outside quotes.

    A command substitution (`$(...)` or backticks), outside quotes or inside double quotes, becomes a segment of its own, and the word `SUBSTITUTION` takes its place in the segment around it, so `git -C $(pwd) commit` keeps an argument where the directory goes.
    A heredoc body is text the command reads on stdin, so it belongs to no segment: `git commit -F - <<'EOF'` with a message line starting `grep` holds no `grep` command. A `<<` whose body no line ends counts as no heredoc, because a shift inside arithmetic (`((1<<2))`) matches `HEREDOC` too.
    """
    segments, buf, quote, i, n = [], [], None, 0, len(command)
    open_substitutions = []
    # Heredocs opened on the current line, whose bodies start after its newline.
    heredocs = []
    # Subshell parentheses open at the current nesting level; a `)` closes a substitution only when none are open.
    open_parens = 0
    while i < n:
        ch = command[i]
        pair = command[i : i + 2]
        closer = open_substitutions[-1].closer if open_substitutions else None
        if ch == "\\" and quote != "'" and i + 1 < n:
            buf.append(pair)
            i += 2
            continue
        arithmetic = ARITHMETIC.match(command, i) if quote != "'" else None
        if arithmetic:
            buf.append(arithmetic[0])
            i = arithmetic.end()
            continue
        if quote != "'" and (pair == "$(" or (ch == "`" and closer != "`")):
            open_substitutions.append(OpenSubstitution(buf, ")" if ch == "$" else "`", open_parens, quote))
            buf, open_parens, quote = [], 0, None
            i += len(pair) if ch == "$" else 1
            continue
        if quote:
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
        if ch == "&" and ((buf and buf[-1] in "><") or command[i + 1 : i + 2] == ">"):
            buf.append(ch)  # part of a redirection (`2>&1`, `<&0`, `&>log`), not an operator
            i += 1
            continue
        if command.startswith("<<<", i):
            buf.append("<<<")  # a here-string, whose text is on this line
            i += 3
            continue
        heredoc = HEREDOC.match(command, i)
        if heredoc:
            heredocs.append(Heredoc(QUOTED_PIECE.sub(lambda piece: "".join(piece.groups("")), heredoc["word"]), heredoc["dash"] == "-"))
            buf.append(heredoc[0])
            i = heredoc.end()
            continue
        body_end = end_of_heredoc_bodies(command, i, heredocs) if ch == "\n" else None
        heredocs = [] if ch == "\n" else heredocs
        if body_end is not None:
            segments.append(Segment("".join(buf), bool(open_substitutions)))
            buf, i = [], body_end
            continue
        if ch == closer and open_parens == 0:
            segments.append(Segment("".join(buf), True))
            outer = open_substitutions.pop()
            buf, open_parens, quote = [*outer.buf, SUBSTITUTION], outer.open_parens, outer.quote
            i += 1
            continue
        if pair in ("||", "&&", "|&"):
            segments.append(Segment("".join(buf), bool(open_substitutions)))
            buf, i = [], i + 2
            continue
        if ch in "|;\n&()":
            open_parens = max(0, open_parens + (ch == "(") - (ch == ")"))
            segments.append(Segment("".join(buf), bool(open_substitutions)))
            buf, i = [], i + 1
            continue
        buf.append(ch)
        i += 1
    segments.append(Segment("".join(buf), bool(open_substitutions)))
    # A substitution with no closer still holds the segments that enclose it; only the outermost runs at the top level.
    segments.extend(Segment("".join(outer.buf), depth > 0) for depth, outer in enumerate(open_substitutions))
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


def unquote(word):
    r"""Return the word after shell quote removal, so `"grep"`, `'grep'`, and `\grep` all compare equal to `grep`, and `'a "b"'` becomes `a "b"`.

    A word with an unclosed quote loses every quote character and backslash.
    """
    try:
        return "".join(shlex.split(word))
    except ValueError:
        return word.replace("'", "").replace('"', "").replace("\\", "")


def queries_location(words):
    """True when these options to `command` include `-v` or `-V`.

    The scan stops at the first word that is not an option, because that word is
    the program being asked about: `command -p nvim` must not read as `-v`.
    """
    for word in words:
        if not word.startswith("-") or word == "-":
            return False
        if word.startswith("--"):
            continue
        if "v" in word[1:] or "V" in word[1:]:
            return True
    return False


def resolve_head(segment):
    """Return (the command word, its arguments) for a segment, or (None, []).

    The command word keeps any directory it was written with, so a caller that
    cares only about the program name passes it through `program_name`.
    """
    words = [unquote(word) for word in split_words(segment)]
    while words:
        word = words[0]
        if "=" in word.split("/")[0] and not word.startswith("="):
            words = words[1:]  # leading VAR=value assignment
            continue
        prefix = PREFIXES.get(program_name(word))
        if prefix is None:
            break
        if program_name(word) == "command" and queries_location(words[1:]):
            return None, []  # prints where a program lives, runs nothing
        words = after_prefix(words[1:], prefix)
    if not words:
        return None, []
    return words[0], words[1:]


def after_prefix(args, prefix):
    """Return the arguments of a prefix program from the command it runs on: past its options, their values, and its operands."""
    index = 0
    while index < len(args) and args[index].startswith("-") and args[index] != "-":
        if args[index] == "--":
            index += 1
            break
        index += 2 if args[index] in prefix.value_options else 1
    return args[index + prefix.operands :]


def program_name(word):
    """Return the program name in a command word, dropping any directory."""
    return word.rsplit("/", 1)[-1]


def base_name(word):
    """Strip a Windows `.exe` suffix and a trailing version from an interpreter name (`python3.12` and `python.exe` -> `python`)."""
    name = program_name(word).removesuffix(".exe")
    return re.sub(r"[\d.]+$", "", name) or name


def iter_arguments(args, value_flags=()):
    """Yield the arguments that are not a redirection or a flag's value.

    Drops a redirection and the target it points at, and drops the argument
    after a flag in `value_flags`. The flag itself is yielded, so a caller can
    still see that it was given.
    """
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        redirect = REDIRECT.match(arg)
        if redirect:
            skip = not redirect.group("target")
            continue
        if arg in value_flags:
            skip = True
        yield arg


def read_input():
    """Return (the Bash tool input, the resolved directory the command starts in) read from the hook input on stdin.

    Exits 0, which allows the command unchanged, when stdin holds no JSON object:
    a hook that cannot read its input has nothing to say about the command.
    """
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    if not isinstance(payload, dict):
        sys.exit(0)
    return payload.get("tool_input") or {}, Path(payload.get("cwd") or os.getcwd()).resolve()


def deny(reason):
    """Write the PreToolUse decision that blocks the command, and exit."""
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def update_input(tool_input):
    """Write the PreToolUse output that runs the call with `tool_input` in place of the input Claude sent, and exit.

    The output makes no permission decision, so the permission rules still decide whether the call runs.
    """
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": tool_input}}))
    sys.exit(0)
