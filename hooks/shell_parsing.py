#!/usr/bin/env python3
"""Reading a Bash command, and answering the PreToolUse caller, shared by the hooks here.

Each hook decides what a command means.
This module decides where the command's parts begin and end, and how a decision reaches the PreToolUse caller.
A hook imports it by name because Python puts the running script's directory first on `sys.path`.
"""

import json
import re
import sys
from functools import partial, reduce
from typing import NamedTuple

# A redirection, with its target attached (`2>log`) or in the next argument (`2> log`).
REDIRECT = re.compile(r"^(?P<fd>\d*|&)(?P<op>>>|>|<<<|<<-|<<|<)(?P<target>.*)$")

# A heredoc operator and the word naming the line that ends its body (`<<EOF`, `<<-'EOF'`, `<< "EOF"`).
HEREDOC = re.compile(r"<<(?P<dash>-?)[ \t]*(?P<word>(?:'[^']*'|\"[^\"]*\"|\\.|[^\s;|&()<>'\"\\])+)")

# A quoted or backslash-escaped piece of a heredoc word; the group that matched holds the text it stands for.
QUOTED_PIECE = re.compile(r"'([^']*)'|\"([^\"]*)\"|\\(.)")

# Words to skip when locating the head of a segment.
PREFIXES = {
    "sudo", "command", "time", "nice", "nohup", "builtin", "exec", "xargs",
    "env", "then", "do", "else",
}


# The word that stands in for a command substitution in the command around it, since the hook cannot know what the substitution prints.
SUBSTITUTION = "$(...)"


class Segment(NamedTuple):
    """One command between shell operators, and whether a pipe gives it its stdin."""

    text: str
    reads_pipe: bool


class OpenSubstitution(NamedTuple):
    """The segment a command substitution interrupted, resumed when `closer` ends the substitution."""

    buf: list
    reads_pipe: bool
    closer: str
    open_parens: int


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
    """Return the command's segments, splitting on shell operators outside quotes.

    A command substitution (`$(...)` or backticks) outside quotes becomes a segment of its own, and the word `SUBSTITUTION` takes its place in the segment around it, so `rg x $(git ls-files)` keeps an argument where the file names go.
    A heredoc body is text the command reads on stdin, so it belongs to no segment: `git commit -F - <<'EOF'` with a message line starting `grep` holds no `grep` command. A `<<` whose body no line ends counts as no heredoc, because a shift inside arithmetic (`$((1<<2))`) matches `HEREDOC` too.
    """
    segments, buf, quote, i, n = [], [], None, 0, len(command)
    reads_pipe = False
    open_substitutions = []
    # Heredocs opened on the current line, whose bodies start after its newline.
    heredocs = []
    # Subshell parentheses open at the current nesting level; a `)` closes a substitution only when none are open.
    open_parens = 0
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
        if ch == "&" and ((buf and buf[-1] in "><") or command[i + 1 : i + 2] == ">"):
            buf.append(ch)  # part of a redirection (`2>&1`, `<&0`, `&>log`), not an operator
            i += 1
            continue
        pair = command[i : i + 2]
        closer = open_substitutions[-1].closer if open_substitutions else None
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
            segments.append(Segment("".join(buf), reads_pipe))
            buf, reads_pipe, i = [], False, body_end
            continue
        if pair == "$(" or (ch == "`" and closer != "`"):
            open_substitutions.append(
                OpenSubstitution(buf, reads_pipe, ")" if ch == "$" else "`", open_parens)
            )
            buf, reads_pipe, open_parens = [], False, 0
            i += len(pair) if ch == "$" else 1
            continue
        if ch == closer and open_parens == 0:
            segments.append(Segment("".join(buf), reads_pipe))
            outer = open_substitutions.pop()
            buf, reads_pipe, open_parens = [*outer.buf, SUBSTITUTION], outer.reads_pipe, outer.open_parens
            i += 1
            continue
        if pair in ("||", "&&", "|&"):
            segments.append(Segment("".join(buf), reads_pipe))
            reads_pipe = pair == "|&"
            buf, i = [], i + 2
            continue
        if ch in "|;\n&()":
            open_parens = max(0, open_parens + (ch == "(") - (ch == ")"))
            segments.append(Segment("".join(buf), reads_pipe))
            reads_pipe = ch == "|"
            buf, i = [], i + 1
            continue
        buf.append(ch)
        i += 1
    segments.append(Segment("".join(buf), reads_pipe))
    segments.extend(Segment("".join(outer.buf), outer.reads_pipe) for outer in open_substitutions)
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
    """Remove shell quote characters, so `"."` and `'.'` both compare equal to `.`."""
    return word.replace("'", "").replace('"', "")


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
    saw_prefix = False
    while words:
        word = words[0]
        if "=" in word.split("/")[0] and not word.startswith("="):
            words = words[1:]  # leading VAR=value assignment
            continue
        if word in PREFIXES:
            if word == "command" and queries_location(words[1:]):
                return None, []  # prints where a program lives, runs nothing
            words, saw_prefix = words[1:], True
            continue
        if word.startswith("-") and saw_prefix:
            words = words[1:]  # options belonging to a skipped prefix word
            continue
        break
    if not words:
        return None, []
    return words[0], words[1:]


def program_name(word):
    """Return the program name in a command word, dropping any directory."""
    return word.rsplit("/", 1)[-1]


def base_name(word):
    """Strip a trailing version from an interpreter name (`python3.12` -> `python`)."""
    name = program_name(word)
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
    """Return (the Bash command, the whole hook input) read from stdin.

    Exits 0, which allows the command, when stdin holds no JSON object: a hook
    that cannot read its input has nothing to say about the command.
    """
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    if not isinstance(payload, dict):
        sys.exit(0)
    return (payload.get("tool_input") or {}).get("command") or "", payload


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
