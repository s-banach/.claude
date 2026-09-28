"""Rule for `bash-rules.py`: deny `cd`, `pushd`, and `popd`.

The hook input's `cwd` is the directory a command starts in, so after a `cd` the other rules judge the rest of the command against the wrong directory.
The next command may not start in that directory either: Claude Code moves the shell back to the project directory after a `cd` out of it.
A command that names its directories, with absolute paths or a program's directory flag, does the same thing whatever directory it starts in.
"""

from shell_parsing import program_name, resolve_head

DIRECTORY_CHANGERS = {"cd", "pushd", "popd"}


def directory_changer(segment):
    """Return the name of the directory-changing command this segment runs, or None."""
    word, _ = resolve_head(segment.text)
    if word is None:
        return None
    name = program_name(word)
    return name if name in DIRECTORY_CHANGERS else None


def verdict(segments, cwd):
    """Return the reason the command is denied, or None."""
    name = next(filter(None, map(directory_changer, segments)), None)
    if name is None:
        return None
    return (
        f"`{name}` changes the directory the rest of the command runs in, which the other rules cannot see. "
        "Use absolute paths, or the program's own directory flag (`git -C <dir>`, `uv run --directory <dir>`)."
    )
