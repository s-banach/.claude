"""Rule for `bash-rules.py`: deny a `git commit` that runs after another command in the same Bash call.

CLAUDE.md requires Claude to commit only when `git diff --cached --name-only` lists exactly the paths it reviewed.
Any command that runs before the commit in the same call can change the staged files, as `git add` does, and the hook cannot tell which commands leave them alone, so the commit must run as the first command of its call.
A command substitution in the commit's arguments also runs before the commit, so it counts unless it runs only a program in `PRINTING_PROGRAMS`.
Commands after the commit (`git commit -m x && git log -1`) cannot change what it commits, so they are left alone.
"""

from shell_parsing import iter_arguments, program_name, resolve_head

# Programs that print text and stage nothing, so a command substitution that runs one in the commit's arguments (`git commit -F $(mktemp)`) leaves the staged files as Claude last read them.
PRINTING_PROGRAMS = {"cat", "echo", "printf", "mktemp"}

# git options before the subcommand that take the next argument as their value.
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--attr-source"}


def git_subcommand(args):
    """Return the git subcommand in these arguments to `git`, skipping git's own options, or None."""
    return next((arg for arg in iter_arguments(args, GIT_VALUE_OPTIONS) if not arg.startswith("-")), None)


def is_commit(word, args):
    """True when the command word and arguments run `git commit`."""
    return word is not None and program_name(word) == "git" and git_subcommand(args) == "commit"


def counts_as_command(segment):
    """True when the segment is a command that keeps a later `git commit` from running first: any nonblank segment, except one inside a command substitution that runs a program in `PRINTING_PROGRAMS`."""
    word, _ = resolve_head(segment.text)
    printing = word is not None and program_name(word) in PRINTING_PROGRAMS
    return bool(segment.text.strip()) and not (segment.inside_substitution and printing)


def verdict(segments, cwd):
    """Return the reason the command is denied, or None."""
    commands = [segment.text for segment in segments if counts_as_command(segment)]
    if not any(is_commit(*resolve_head(text)) for text in commands[1:]):
        return None
    return (
        "`git commit` runs after another command in this call, so it commits a state Claude has not checked. "
        "Run the other commands in their own call, confirm that `git diff --cached --name-only` lists exactly the reviewed paths, "
        "then run `git commit` as the first command of a new call."
    )
