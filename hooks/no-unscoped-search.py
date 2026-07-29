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

from shell_parsing import (
    deny,
    iter_arguments,
    program_name,
    read_input,
    resolve_head,
    split_segments,
)

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

ALTERNATIVE = (
    "Name a subdirectory or the files to search, and leave ignore rules on."
)


def positionals(args, drop_first):
    """Return the non-option arguments, dropping the first one when it is a pattern.

    Redirections and their targets are not search paths, so `grep -r x src/ 2>log`
    is scoped to `src/`.
    """
    found = []
    for arg in iter_arguments(args, VALUE_OPTIONS):
        if arg == "--":
            continue
        if arg.startswith("-") and arg != "-":
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
    word, args = resolve_head(segment)
    if word is None:
        return None
    head = program_name(word)
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
    command, _ = read_input()
    for segment in split_segments(command):
        reason = verdict(segment)
        if reason:
            deny(f"{reason} {ALTERNATIVE}")


if __name__ == "__main__":
    main()
