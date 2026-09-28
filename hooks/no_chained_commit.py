"""Rule for `bash-rules.py`: deny a `git commit` that runs after another command in the same Bash call.

A command before the commit is usually a check, and chaining it to the commit lets the shell judge the check by an exit status that can lie: in `pytest | tail && git commit`, `&&` reads the exit status of `tail`, so failing tests still commit.
Run in separate calls, Claude reads the check's output before deciding to commit.
Commands after the commit (`git commit -m x && git log -1`) cannot change whether it happens, so they are left alone.
"""

from shell_parsing import iter_arguments, program_name, resolve_head

# git options before the subcommand that take the next argument as their value.
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--attr-source"}


def git_subcommand(args):
    """Return the git subcommand in these arguments to `git`, skipping git's own options, or None."""
    return next((arg for arg in iter_arguments(args, GIT_VALUE_OPTIONS) if not arg.startswith("-")), None)


def is_commit(word, args):
    """True when the command word and arguments run `git commit`."""
    return word is not None and program_name(word) == "git" and git_subcommand(args) == "commit"


def verdict(segments, cwd):
    """Return the reason the command is denied, or None."""
    commands = [segment.text for segment in segments if segment.text.strip()]
    if not any(is_commit(*resolve_head(text)) for text in commands[1:]):
        return None
    return (
        "`git commit` runs after another command in this call, so the shell decides whether to commit from an exit status Claude has not read. "
        "Run the checks in their own call, read their output, then run `git commit` as the first command of a new call."
    )
