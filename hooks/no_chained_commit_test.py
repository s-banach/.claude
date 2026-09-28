#!/usr/bin/env python3
"""Check no_chained_commit.py against commands whose verdict is known.

Run `python3 ~/.claude/hooks/no_chained_commit_test.py` after editing the rule.
Each case is (command, denied), where denied is True when the rule must block it.
"""

import no_chained_commit
from hook_testing import check, report

CASES = [
    # A commit after another command, whatever joins them: denied.
    ("pytest | tail && git commit -m x", True),
    ("pytest; git commit -m x", True),
    ("pytest || git commit -m x", True),
    ("pytest\ngit commit -m x", True),
    ("git add a.py && git commit -m x", True),
    ("if pytest; then git commit -m x; fi", True),
    ("pytest && git -C repo commit -m x", True),
    ("pytest && git -c user.name=x commit -m x", True),
    ("pytest && /usr/bin/git commit -m x", True),
    ("X=\"$(pytest | tail)\" && git commit -m x", True),
    ("command -v pytest && git commit -m x", True),
    ("pytest && git --attr-source HEAD commit -m x", True),
    # The unquoted substitution runs before the commit, so it counts as a command before it.
    ("git commit -F $(mktemp)", True),
    # A commit that runs first: allowed, with anything after it.
    ("git commit -m x", False),
    ("git commit -m x && git log -1", False),
    ("git -C repo commit -m x; git log -1", False),
    ("(git commit -m x)", False),
    ("\ngit commit -m x", False),
    ("X=1 git commit -m x", False),
    ("git commit -m \"$(cat <<'EOF'\nSubject\n\npytest | tail\nEOF\n)\"", False),
    ("git commit -F - <<'EOF'\nSubject\n\nran pytest && git status\nEOF", False),
    # Other git subcommands, and `commit` as an argument: allowed.
    ("pytest && git status", False),
    ("git log && git show HEAD", False),
    ("pytest && echo git commit", False),
    ("pytest && git log --grep commit", False),
]


def main():
    report(check(no_chained_commit, CASES), len(CASES))


if __name__ == "__main__":
    main()
