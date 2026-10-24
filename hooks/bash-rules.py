#!/usr/bin/env python3
"""PreToolUse hook for Bash: deny a command that breaks any rule in `RULES`, giving the reason from every rule it breaks, and otherwise make Claude Code kill a foreground call that runs too long, with `foreground_timeout.limited_input`.

Reads the hook input JSON on stdin and writes a PreToolUse output on stdout.
Every rule lives in one hook, so each Bash call starts one Python process and parses the command once.
Each rule module has a `verdict(segments, cwd)` that returns the reason it denies the command, or None.
The rules judge the command Claude sent, before `limited_input` changes it.
"""

import foreground_timeout
import no_cd
import no_chained_commit
import no_grep
import no_python_outside_venv
from shell_parsing import deny, read_input, split_segments, update_input

RULES = (no_grep, no_python_outside_venv, no_cd, no_chained_commit)


def main():
    tool_input, cwd = read_input()
    segments = split_segments(tool_input.get("command") or "")
    reasons = [reason for rule in RULES if (reason := rule.verdict(segments, cwd))]
    if reasons:
        deny("\n".join(reasons))
    limited = foreground_timeout.limited_input(tool_input)
    if limited is not None:
        update_input(limited)


if __name__ == "__main__":
    main()
