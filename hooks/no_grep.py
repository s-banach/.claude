"""Rule for `bash-rules.py`: deny a search program other than `rg`.

CLAUDE.md says to search with `rg`, never `grep`, so the grep family and the other searchers are denied, whatever they search.
`git grep` is a git subcommand, so it is left alone.
"""

from shell_parsing import program_name, resolve_head

REPLACED_BY_RIPGREP = {"grep", "egrep", "fgrep", "rgrep", "zgrep", "ag", "ack", "ack-grep"}


def replaced_searcher(segment):
    """Return the name of the search program other than `rg` that this segment runs, or None."""
    word, _ = resolve_head(segment.text)
    name = None if word is None else program_name(word)
    return name if name in REPLACED_BY_RIPGREP else None


def verdict(segments, cwd):
    """Return the reason the command is denied, or None."""
    name = next(filter(None, map(replaced_searcher, segments)), None)
    if name is None:
        return None
    return f"Search with `rg` instead of `{name}`. Use `rg -P` for backreferences or lookaround."
