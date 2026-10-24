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
    ("X=$(pytest | tail) && git commit -m x", True),
    ("pytest && git -C $(pwd) commit -m x", True),
    ("pytest && git 2>/dev/null commit -m x", True),
    ("pytest && git 2> log.txt commit -m x", True),
    ("git commit $(git add -A)", True),
    ("git commit -m `git add -A; echo msg`", True),
    ("pytest && echo $(git commit -m x)", True),
    ("echo $(git add -A; git commit -m x)", True),
    ('git commit -m "$(git add -A; echo msg)"', True),
    ("sh -c 'pytest && git commit -m x'", True),
    ("pytest && sh -c 'git commit -m x'", True),
    # A commit that runs first: allowed, with anything after it, and with substitutions in its arguments that only print text.
    ("git commit -m x", False),
    ("git commit -F $(mktemp)", False),
    ("sh -c 'git commit -m x'", False),
    ('sh -c "git commit -m $(cat msg)"', False),
    ('eval git commit -F "$(mktemp)"', False),
    # Arithmetic runs no command.
    ('git commit -m "Release $((1+1))" && git log -1', False),
    ("git commit -m v$((n*(2+1)))", False),
    ('git commit -m "v$(( ($n+1)*2 ))"', False),
    ("git commit -F `mktemp` && git log -1", False),
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
    report(check(no_chained_commit.verdict, CASES), len(CASES))


if __name__ == "__main__":
    main()
