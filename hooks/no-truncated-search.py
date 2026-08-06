#!/usr/bin/env python3
"""PreToolUse hook for Bash: deny cutting a search's output with `head` or `tail`.

Reads the hook input JSON on stdin and writes a PreToolUse decision on stdout.
A search reports which lines match, so cutting its output changes what the result says: a line that was cut and a line that never matched look the same in what remains.
The hook denies `head` and `tail` only downstream of a search in the same pipeline, where narrowing the pattern or counting the matches answers the question without cutting anything.
Truncating a file, or any other command's output, is left alone.
"""

from shell_parsing import (
    OPTIONAL_RECURSIVE_SEARCH,
    RECURSIVE_SEARCH,
    WALKERS,
    deny,
    program_name,
    read_input,
    resolve_head,
    split_pipelines,
    split_words,
    unquote,
)

SEARCH = RECURSIVE_SEARCH | OPTIONAL_RECURSIVE_SEARCH | WALKERS
TRUNCATORS = {"head", "tail"}

ALTERNATIVE = (
    "Narrow the search until its whole output fits, or count the matches"
    " instead of listing them."
)


def search_name(word, args):
    """Return the name of the search this command word runs, or None."""
    name = program_name(word)
    if name == "git" and args and args[0] == "grep":
        return "git grep"
    return name if name in SEARCH else None


def truncator_name(word, segment):
    """Return `head` or `tail` when this command word runs one, or None.

    `xargs` turns the previous segment's output into arguments, so `xargs head` prints from every file the search named and cuts none of the search's own output.
    """
    name = program_name(word)
    if name not in TRUNCATORS:
        return None
    if "xargs" in [unquote(seen) for seen in split_words(segment)]:
        return None
    return name


def verdict(pipeline):
    """Return the reason this pipeline is denied, or None."""
    upstream = None
    for segment in pipeline:
        word, args = resolve_head(segment)
        if word is None:
            continue
        truncator = truncator_name(word, segment)
        if truncator and upstream:
            return (
                f"`{truncator}` cuts the output of `{upstream}`, and a line it cut"
                " is indistinguishable from a line that never matched."
            )
        upstream = upstream or search_name(word, args)
    return None


def main():
    command, _ = read_input()
    for pipeline in split_pipelines(command):
        reason = verdict(pipeline)
        if reason:
            deny(f"{reason} {ALTERNATIVE}")


if __name__ == "__main__":
    main()
