#!/usr/bin/env python3
"""PreToolUse hook for Bash: deny a recursive search that names no scope.

Reads the hook input JSON on stdin and writes a PreToolUse decision on stdout.
The cost of a search lives in the tree it walks, which this hook cannot see, so
it judges the one thing the command text does show: whether the walk is bounded.
A recursive search is denied when its root is the whole working tree (`.`, `/`,
`~`, or no path at all), when its root is a directory that holds dependencies or
build output, or when a flag switches the walker's ignore rules off. A search
given a subdirectory, named files, a depth cap, or a pipe is left alone.
"""

import json
import re
import sys

# A redirection, with its target attached (`2>log`) or in the next argument (`2> log`).
REDIRECT = re.compile(r"^(?:\d*|&)(?:>>|>|<<|<)(?P<target>.*)$")

# Recursive by default: naming no path searches the whole tree.
RECURSIVE_SEARCH = {"rg", "ripgrep", "ag", "ack", "ack-grep"}
# Recursive only with a flag, and then with no ignore rules at all.
OPTIONAL_RECURSIVE_SEARCH = {"grep", "egrep", "fgrep", "rgrep", "zgrep"}
WALKERS = {"find", "fd", "fdfind"}

# Roots that mean "everything from here".
BROAD_ROOTS = {".", "./", "/", "~", "~/", "$HOME", "${HOME}", "*"}
# Directories whose size is the reason this hook exists.
HEAVY_DIRS = {
    ".venv", "venv", "env", "node_modules", "target", "build", "dist", "vendor",
    ".git", ".tox", ".mypy_cache", ".pytest_cache", "__pycache__",
    "site-packages", ".cargo", ".rustup", ".gradle", ".m2", "Library",
}
# Flags that switch a walker's ignore rules off.
UNRESTRICTED_FLAGS = {
    "--no-ignore", "--no-ignore-vcs", "--no-ignore-global", "--no-ignore-parent",
    "--no-ignore-dot", "--unrestricted",
}
# Options that consume the argument after them, so it is not a path.
VALUE_OPTIONS = {
    "-e", "-f", "-m", "-A", "-B", "-C", "-d", "-g", "-t", "-T", "-M", "-j",
    "--regexp", "--file", "--max-count", "--include", "--exclude",
    "--exclude-dir", "--glob", "--type", "--type-not", "--after-context",
    "--before-context", "--context", "--threads", "--directories",
    "--max-depth", "--min-depth",
    # find primaries: their value is a name, a size, or a time, never a path.
    "-name", "-iname", "-path", "-ipath", "-regex", "-iregex", "-type",
    "-size", "-perm", "-user", "-group", "-links", "-inum", "-mtime",
    "-mmin", "-newer", "-anewer", "-cnewer", "-maxdepth", "-mindepth",
}
# Words to skip when locating the head of a segment.
PREFIXES = {
    "sudo", "command", "time", "nice", "nohup", "builtin", "exec", "xargs",
    "then", "do", "else",
}

ALTERNATIVE = (
    "Name a subdirectory or the files to search, and leave ignore rules on."
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


def unquote(word):
    """Remove shell quote characters, so `"."` and `'.'` both compare equal to `.`."""
    return word.replace("'", "").replace('"', "")


def resolve_head(segment):
    """Return (program name, its arguments) for a segment, or (None, [])."""
    words = [unquote(word) for word in split_words(segment)]
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


def positionals(args, drop_first):
    """Return the non-option arguments, dropping the first one when it is a pattern.

    Redirections and their targets are not search paths, so `grep -r x src/ 2>log`
    is scoped to `src/`.
    """
    found, skip = [], False
    for arg in args:
        if skip:
            skip = False
            continue
        redirect = REDIRECT.match(arg)
        if redirect:
            skip = not redirect.group("target")
            continue
        if arg == "--":
            continue
        if arg.startswith("-") and arg != "-":
            if arg in VALUE_OPTIONS:
                skip = True
            continue
        found.append(arg)
    if drop_first and found:
        found = found[1:]
    return found


def is_broad(root):
    """True when this root walks the whole tree or a dependency directory."""
    stripped = root.rstrip("/") or "/"
    if root in BROAD_ROOTS or stripped in BROAD_ROOTS:
        return True
    return any(part in HEAVY_DIRS for part in stripped.split("/") if part)


def backticked(roots):
    """Join roots for a message, each in backticks, so a root of `.` is not read
    as the sentence period."""
    return " ".join(f"`{root}`" for root in roots)


def bounded_by_depth(args):
    """True when a maxdepth option caps the walk."""
    for i, arg in enumerate(args):
        if arg in ("-maxdepth", "--max-depth", "-depth-limit"):
            return True
        if arg.startswith("--max-depth=") or arg.startswith("-maxdepth="):
            return True
        if arg == "-d" and i + 1 < len(args) and args[i + 1].isdigit():
            return True
    return False


def defeats_ignore_rules(arg):
    """True for a flag that makes a walker search ignored directories."""
    if arg in UNRESTRICTED_FLAGS:
        return True
    bundled_short = arg.startswith("-") and not arg.startswith("--")
    return bundled_short and set(arg[1:]) == {"u"}  # -u, -uu, -uuu


def grep_is_recursive(args):
    """True when a grep-family invocation was told to walk directories."""
    for i, arg in enumerate(args):
        if arg in ("--recursive", "-r", "-R", "--dereference-recursive"):
            return True
        if arg.startswith("--directories") and "recurse" in arg:
            return True
        if arg == "-d" and i + 1 < len(args) and args[i + 1] == "recurse":
            return True
        if arg.startswith("-") and not arg.startswith("--") and ("r" in arg[1:] or "R" in arg[1:]):
            return True  # bundled short options such as -rn
    return False


def verdict(segment):
    """Return the reason this segment is denied, or None."""
    head, args = resolve_head(segment)
    if head is None:
        return None
    if head == "git" and args and args[0] == "grep":
        return None  # searches tracked files only, so no dependency directory is walked
    if head in WALKERS:
        roots = positionals(args, drop_first=False) or ["."]
        if bounded_by_depth(args):
            return None
        if any(is_broad(root) for root in roots):
            return f"`{head}` walks the whole tree from {backticked(roots)}."
        return None
    if head in RECURSIVE_SEARCH or head in OPTIONAL_RECURSIVE_SEARCH:
        if head in OPTIONAL_RECURSIVE_SEARCH and not grep_is_recursive(args):
            return None  # reads the named files or stdin
        unrestricted = [arg for arg in args if defeats_ignore_rules(arg)]
        if unrestricted:
            return f"`{head} {unrestricted[0]}` searches ignored directories."
        if bounded_by_depth(args):
            return None  # the walk is capped, so its root does not matter
        drop_first = not any(a in ("-e", "-f", "--regexp", "--file") for a in args)
        roots = positionals(args, drop_first=drop_first)
        if not roots:
            return f"`{head}` searches the whole working tree when no path is given."
        if any(is_broad(root) for root in roots):
            return f"`{head}` walks the whole tree from {backticked(roots)}."
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    command = (payload.get("tool_input") or {}).get("command") or ""
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
