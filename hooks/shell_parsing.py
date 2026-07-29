#!/usr/bin/env python3
"""Reading a Bash command, and answering the PreToolUse caller, shared by the hooks here.

Each hook decides what a command means; this module decides where the command's
parts begin and end, and how a decision reaches the PreToolUse caller. A hook
imports it by name because Python puts the running script's directory first on
`sys.path`.
"""

import json
import re
import sys

# A redirection, with its target attached (`2>log`) or in the next argument (`2> log`).
REDIRECT = re.compile(r"^(?P<fd>\d*|&)(?P<op>>>|>|<<<|<<|<)(?P<target>.*)$")

# Words to skip when locating the head of a segment.
PREFIXES = {
    "sudo", "command", "time", "nice", "nohup", "builtin", "exec", "xargs",
    "env", "then", "do", "else",
}


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


def redirects_stdin_from_file(args):
    """True when a `< file` redirection gives the command its stdin.

    The target follows in the next argument when it is not attached, as in
    `< file`. A target starting with `&` names another descriptor rather than a
    file, and `split_segments` breaks on `&`, so `<&0` reaches here as a `<`
    with nothing after it; neither spelling points stdin at a file.
    """
    for index, arg in enumerate(args):
        redirect = REDIRECT.match(arg)
        if not redirect or redirect.group("op") != "<" or redirect.group("fd"):
            continue
        target = redirect.group("target")
        if not target and index + 1 < len(args):
            target = args[index + 1]
        if target and not target.startswith("&"):
            return True
    return False


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
