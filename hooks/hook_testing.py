#!/usr/bin/env python3
"""Running a rule of `bash-rules.py` against commands whose verdict is known, shared by the tests here."""

import sys

from shell_parsing import split_segments


def check(rule, cases, cwd=None, note=""):
    """Print a line for each case `rule` gets wrong; return how many there were.

    `rule` is a rule module, and `cwd` the directory each command starts in.
    """
    failures = 0
    for command, denied in cases:
        if bool(rule.verdict(split_segments(command), cwd)) == denied:
            continue
        failures += 1
        want = "DENY" if denied else "allow"
        print(f"FAIL want {want}{note}: {command}")
    return failures


def report(failures, total):
    """Print the pass count and exit non-zero when any case failed."""
    print(f"{total - failures}/{total} cases pass")
    sys.exit(1 if failures else 0)
