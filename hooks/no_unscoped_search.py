"""Rule for `bash-rules.py`: deny a search that is not `rg`, and an `rg` or file walk that names no scope.

CLAUDE.md says to search with `rg`, never `grep`, so the grep family and the other searchers are denied outright; `git grep` is a git subcommand and is left alone.
In Claude Code's Bash, stdin is a pipe that never closes, so an `rg` given no path and fed by no pipe waits on stdin forever.
The cost of a walk lives in the tree it walks, which this rule cannot see, so it judges the one thing the command text does show: whether the walk is bounded.
An `rg` or a file walker is denied when its root is the whole working tree (`.`, `/`, `~`), when its root is a directory that holds dependencies or build output, or when a flag switches the walker's ignore rules off.
A search given a subdirectory, named files, a depth cap, or a pipe is left alone.
"""

from shell_parsing import iter_arguments, program_name, resolve_head

RIPGREP = {"rg", "ripgrep"}
REPLACED_BY_RIPGREP = {"grep", "egrep", "fgrep", "rgrep", "zgrep", "ag", "ack", "ack-grep"}
WALKERS = {"find", "fd", "fdfind"}
# `rg` options that print information and search nothing.
INFO_OPTIONS = {"--version", "-V", "--help", "-h", "--type-list"}
# `rg` options that give the pattern, so the first positional is a path.
PATTERN_OPTIONS = {"-e", "-f", "--regexp", "--file"}
# Roots that mean "everything from here".
BROAD_ROOTS = {".", "./", "/", "~", "~/", "$HOME", "${HOME}", "*"}
# Directories whose size is the reason this rule exists.
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
    "--regexp", "--file", "--max-count", "--glob", "--type", "--type-not",
    "--after-context", "--before-context", "--context", "--threads",
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

    Redirections and their targets are not search paths, so `rg x src/ 2>log`
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


def walk_verdict(head, roots, args):
    """Return the reason a walk from these roots is denied, or None."""
    unrestricted = [arg for arg in args if defeats_ignore_rules(arg)]
    if unrestricted:
        return f"`{head} {unrestricted[0]}` searches ignored directories. {ALTERNATIVE}"
    if bounded_by_depth(args):
        return None
    if any(is_broad(root) for root in roots):
        return f"`{head}` walks the whole tree from {backticked(roots)}. {ALTERNATIVE}"
    return None


def ripgrep_verdict(head, args, reads_pipe):
    """Return the reason this `rg` is denied, or None."""
    if any(arg in INFO_OPTIONS for arg in args):
        return None
    if "--files" in args:
        return walk_verdict(head, positionals(args, drop_first=False) or ["."], args)
    drop_first = not any(arg in PATTERN_OPTIONS for arg in args)
    roots = positionals(args, drop_first=drop_first)
    if roots:
        return walk_verdict(head, roots, args)
    if reads_pipe:
        return None
    return f"`{head}` with no path reads stdin, which never closes in Claude Code's Bash, so it hangs. {ALTERNATIVE}"


def segment_verdict(segment):
    """Return the reason this segment is denied, or None."""
    word, args = resolve_head(segment.text)
    if word is None:
        return None
    head = program_name(word)
    if head in REPLACED_BY_RIPGREP:
        return f"Search with `rg` instead of `{head}`. Use `rg -P` for backreferences or lookaround."
    if head in RIPGREP:
        return ripgrep_verdict(head, args, segment.reads_pipe)
    if head in WALKERS:
        return walk_verdict(head, positionals(args, drop_first=False) or ["."], args)
    return None


def verdict(segments, cwd):
    """Return the reason the command is denied, or None."""
    return next(filter(None, map(segment_verdict, segments)), None)
