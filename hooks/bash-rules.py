#!/usr/bin/env python3
"""PreToolUse hook for Bash: deny a command that breaks any rule in `RULES`, giving the reason from every rule it breaks.

Reads the hook input JSON on stdin and writes a PreToolUse decision on stdout.
Every rule lives in one hook, so each Bash call starts one Python process and parses the command once.
Each rule module has a `verdict(segments, cwd)` that returns the reason it denies the command, or None.
"""

import no_cd
import no_chained_commit
import no_python_outside_venv
import no_unscoped_search
from shell_parsing import deny, read_input, split_segments

RULES = (no_unscoped_search, no_python_outside_venv, no_cd, no_chained_commit)


def main():
    command, cwd = read_input()
    segments = split_segments(command)
    reasons = [reason for rule in RULES if (reason := rule.verdict(segments, cwd))]
    if reasons:
        deny("\n".join(reasons))


if __name__ == "__main__":
    main()
