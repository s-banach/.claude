#!/usr/bin/env python3
"""Check no_grep.py against commands whose verdict is known.

Run `python3 ~/.claude/hooks/no_grep_test.py` after editing the rule or `shell_parsing.py`.
Each case is (command, denied), where denied is True when the rule must block it.
Most cases check where `shell_parsing.split_segments` finds commands, using `grep` as the command to find.
"""

import no_grep
from hook_testing import check, report

CASES = [
    # A searcher other than rg: denied, wherever it sits and whatever it reads.
    ("grep -n TODO crate/src/engine.rs", True),
    ("cargo test 2>&1 | grep -c FAILED", True),
    ("/usr/bin/grep -r TODO crate/src", True),
    ("sudo egrep -r secret /", True),
    ("ag pattern src", True),
    ("if grep -q x notes.txt; then :; fi", True),
    ("! grep x notes.txt", True),
    ("\\grep x notes.txt", True),
    ("command -p grep x notes.txt", True),
    ("cargo test |& grep FAILED", True),
    ("command grep -v x notes.txt", True),
    # A prefix program's options, their values, and its operands come before the command it runs.
    ("sudo -u bob grep x notes.txt", True),
    ("env -u FOO grep x notes.txt", True),
    ("nice -n 10 grep x notes.txt", True),
    ("xargs -n 1 grep x", True),
    ("xargs -I {} grep x {}", True),
    ("timeout 10 grep x notes.txt", True),
    ("timeout -s KILL 10 grep x notes.txt", True),
    ("sudo --user bob grep x notes.txt", True),
    ("env --unset FOO grep x notes.txt", True),
    ("nice --adjustment 10 grep x notes.txt", True),
    ("xargs --max-args 1 grep x", True),
    ("timeout 10 rg x src", False),
    # A command substitution inside double quotes runs too; inside single quotes or escaped, it is text.
    ('echo "$(grep x notes.txt)"', True),
    ('echo "`grep x notes.txt`"', True),
    ("echo '$(grep x notes.txt)'", False),
    ('echo "\\$(grep x notes.txt)"', False),
    ('echo "a $(echo "b c") grep x"', False),
    # A command string run as shell code is split into commands too.
    ("sh -c 'grep x notes.txt'", True),
    ("bash -lc 'ls && grep x notes.txt'", True),
    ("bash -o pipefail -c 'grep x notes.txt'", True),
    ("bash -euo pipefail -c 'grep x notes.txt'", True),
    ('echo "$(( $(grep -c x notes.txt) + 1 ))"', True),
    ("eval 'grep x notes.txt'", True),
    ("sh -c 'sh -c \"grep x notes.txt\"'", True),
    ("xargs sh -c 'grep x \"$@\"' _", True),
    ("sh -c \"echo 'x; grep y'\"", False),
    ("bash script.sh grep", False),
    # A command substitution is a command of its own, and the command around it is still checked.
    ("echo $(grep TODO notes.txt)", True),
    ("echo `grep TODO notes.txt`", True),
    ("echo $(cd crate; (grep TODO src)) done", True),
    ("echo $(cd crate; (ls src)) grep x", False),
    ("rg -n TODO $(git ls-files) && grep x notes.txt", True),
    # A heredoc body is text on stdin, and the commands after it are still checked.
    ("git commit -F - <<'EOF'\nSubject\n\ngrep is replaced by rg\nEOF", False),
    ("echo $(cat <<EOF\ngrep x\nEOF\n)", False),
    ('cat <<-"EOF"\n\tgrep x\n\tEOF\nls', False),
    ("paste <<A <<B\ngrep 1\nA\ngrep 2\nB", False),
    ("cat <<EOF > notes.txt\ngrep x\nEOF\ngrep y notes.txt", True),
    ("cat <<< 'x'\ngrep y notes.txt", True),
    ("cat <<'E\\OF'\ngrep x\nE\\OF\nls", False),
    ("cat <<'it'\"'\"'s'\ngrep x\nit's\nls", False),
    # A `<<` whose body no line ends is no heredoc, so the lines after it are still checked.
    ("echo $((1<<2))\ngrep -r x /", True),
    ("(( x <<= 1 ))\ngrep y notes.txt", True),
    # The word grep as an argument, in a string, or as a git subcommand: allowed.
    ("git grep engine", False),
    ("rg TODO crate/src", False),
    ("echo 'the word grep in a string'", False),
    ('python3 -c "s = \\"a | grep -r b\\"; print(s)"', False),
    ("command -v grep", False),
    ("command -V grep", False),
]


def main():
    report(check(no_grep.verdict, CASES), len(CASES))


if __name__ == "__main__":
    main()
