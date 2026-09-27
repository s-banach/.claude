#!/usr/bin/env python3
"""Check no-unscoped-search.py against commands whose verdict is known.

Run `python3 no-unscoped-search-test.py` from this directory after editing the hook.
Each case is (command, denied), where denied is True when the hook must block it.
"""

from pathlib import Path

from hook_testing import check, report

HOOK = str(Path(__file__).with_name("no-unscoped-search.py"))

CASES = [
    # A searcher other than rg: denied, whatever its scope.
    ("grep -n TODO crate/src/engine.rs", True),
    ("cargo test 2>&1 | grep -c FAILED", True),
    ("grep -r TODO crate/src", True),
    ("/usr/bin/grep -r TODO crate/src", True),
    ("sudo egrep -r secret /", True),
    ("ag pattern src", True),
    # rg with no path and no pipe: denied.
    ("rg TODO", True),
    ("rg -e TODO", True),
    ("rg --max-depth 5 -l TODO", True),
    ("cd /tmp && rg x", True),
    # rg with no path reading a pipe: allowed.
    ("cargo test 2>&1 | rg -c FAILED", False),
    ("git diff -W crate/src/engine.rs | rg -v '^[+-]'", False),
    ("cargo test |& rg FAILED", False),
    # A pipe feeds only the segment right after it.
    ("cargo test | sort; rg x", True),
    # A command substitution supplies the outer command's arguments, and its own command is still checked.
    ("rg -n TODO $(git ls-files)", False),
    ("rg -n TODO `git ls-files`", False),
    ("rg TODO $(git ls-files) crate/src", False),
    ("rg TODO $(git ls-files) .", True),
    ("echo $(grep TODO notes.txt)", True),
    ("echo `rg TODO`", True),
    ("echo $(cd crate; (rg TODO src)) done", False),
    ("echo $(cd crate; (rg TODO)) done", True),
    ('rg "$(cat pattern.txt)"', True),
    ("(cd crate && rg TODO src)", False),
    ("(cd crate && rg TODO)", True),
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
    # rg that searches nothing: allowed.
    ("rg --version", False),
    ("rg --type-list", False),
    # Recursive search with no scope: denied.
    ("rg TODO .", True),
    ('rg pattern "."', True),
    ("rg pattern '.'", True),
    ('rg pattern "$HOME"', True),
    ("rg --files", True),
    ("rg --files -g '*.py'", True),
    # Recursive search rooted in a dependency or build directory: denied.
    ("rg pattern .venv", True),
    ("rg pattern node_modules", True),
    ("rg pattern crate/target/debug", True),
    ('rg TODO "my dir/node_modules"', True),
    ("find node_modules -name '*.json'", True),
    # Ignore rules switched off: denied.
    ("rg -uu pattern src/", True),
    ("rg --no-ignore pattern src/", True),
    # Unbounded walk: denied.
    ("find . -name '*.rs'", True),
    ("find", True),
    ("find / -name x", True),
    ("fd -e rs", True),
    # Scoped search: allowed.
    ("rg TODO crate/src", False),
    ("rg -t rust TODO crate/src", False),
    ("rg -e TODO crate/src", False),
    ("rg --files crate/src", False),
    ("rg -n TODO crate/src/engine.rs", False),
    ('rg TODO "my dir"', False),
    ("find crate/src -name '*.rs'", False),
    ("find . -maxdepth 1 -name '*.toml'", False),
    ("rg --max-depth 1 pattern .", False),
    ("rg --max-depth=1 pattern .", False),
    # An option's value is not a search path.
    ("find src -name node_modules", False),
    ("find crate/src -name .venv", False),
    ("rg pattern src -g '!node_modules'", False),
    # Redirections are not search paths.
    ("rg pattern crate/src 2>/dev/null", False),
    ("rg pattern crate/src > .venv/out.txt", False),
    ("rg pattern crate/src 2> log.txt", False),
    # Untouched commands.
    ("git grep engine", False),
    ("ls -la", False),
    ("cat notes.txt", False),
    ("./scripts/lint.sh", False),
    ("echo 'the word grep in a string'", False),
    ('python3 -c "s = \\"a | grep -r b\\"; print(s)"', False),
    # `command -v` prints where a program lives and runs nothing.
    ("command -v rg", False),
    ("command -V grep", False),
    ("command -p rg pattern .", True),
    ("command rg -v pattern .", True),
]


def main():
    report(check(HOOK, CASES), len(CASES))


if __name__ == "__main__":
    main()
