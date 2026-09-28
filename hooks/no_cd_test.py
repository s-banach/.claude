#!/usr/bin/env python3
"""Check no_cd.py against commands whose verdict is known.

Run `python3 ~/.claude/hooks/no_cd_test.py` after editing the rule.
Each case is (command, denied), where denied is True when the rule must block it.
"""

import no_cd
from hook_testing import check, report

CASES = [
    # A command that changes directory: denied, wherever it sits in the command.
    ("cd src", True),
    ("cd", True),
    ("cd ~/git/proj && python x.py", True),
    ("git status; cd ..", True),
    ("(cd crate && rg TODO src)", True),
    ("echo $(cd src; pwd)", True),
    ("builtin cd /tmp", True),
    ("if cd src; then make; fi", True),
    ("{ cd src; make; }", True),
    ("! cd src", True),
    ("\\cd src", True),
    ("pushd src", True),
    ("popd", True),
    # A command that names its directory: allowed.
    ("git -C ~/git/proj status", False),
    # The word `cd` as an argument, in a heredoc body, or inside another name: allowed.
    ("echo cd", False),
    ("git commit -F - <<'EOF'\nSubject\n\ncd src before running\nEOF", False),
    ("command -v cd", False),
    ("./scripts/cd-helper.sh", False),
    ("abcd x", False),
]


def main():
    report(check(no_cd, CASES), len(CASES))


if __name__ == "__main__":
    main()
