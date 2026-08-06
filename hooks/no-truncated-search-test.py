#!/usr/bin/env python3
"""Check no-truncated-search.py against commands whose verdict is known.

Run `python3 no-truncated-search-test.py` from this directory after editing the hook.
Each case is (command, denied), where denied is True when the hook must block it.
"""

from pathlib import Path

from hook_testing import check, report

HOOK = str(Path(__file__).with_name("no-truncated-search.py"))

CASES = [
    # A search whose output is cut: denied.
    ("rg TODO crate/src | head -20", True),
    ("rg TODO crate/src | head", True),
    ("rg TODO crate/src | tail -20", True),
    ("grep -rn TODO crate/src | head -5", True),
    ("git grep engine | head -20", True),
    ("find crate/src -name '*.rs' | head", True),
    ("fd -e rs crate/src | head -3", True),
    ("ag pattern crate/src | head", True),
    # The cut still happens further down the pipeline, or under another name.
    ("rg TODO crate/src | sort | head -20", True),
    ("rg TODO crate/src | sort -u | uniq | tail -5", True),
    ("rg TODO crate/src |& head -5", True),
    ("rg TODO crate/src | /usr/bin/head -5", True),
    # A redirection's `&` is not the background operator.
    ("rg TODO crate/src 2>&1 | head -5", True),
    ("rg TODO crate/src >&2 | head -5", True),
    ("rg TODO crate/src &> log.txt | head -5", True),
    # A pipeline inside a substitution is still a pipeline.
    ("x=$(rg TODO crate/src | head -5)", True),
    ("echo $(grep -rn TODO crate/src | head -5)", True),
    # The search runs after another command.
    ("cd /tmp && rg TODO crate/src | head -5", True),
    ("cargo build 2>&1 | grep -n error | head -5", True),
    # Truncating a file, not a search: allowed.
    ("head -n 5 data.csv", False),
    ("head -c 64 blob.bin", False),
    ("tail -f server.log", False),
    ("tail -20 crate/src/engine.rs", False),
    # Truncating a command that is not a search: allowed.
    ("git log --oneline | head -5", False),
    ("cat notes.txt | head -20", False),
    ("ls crate/src | head", False),
    ("cargo test 2>&1 | tail -20", False),
    ("ps aux | head -10", False),
    # No output reaches the truncator, so nothing is cut.
    ("rg TODO crate/src && head -5 notes.txt", False),
    ("rg TODO crate/src ; head -5 notes.txt", False),
    ("rg TODO crate/src || tail -5 notes.txt", False),
    ("head -5 paths.txt | rg TODO", False),
    ("rg TODO crate/src & head -5 notes.txt", False),
    # `xargs` makes the search results arguments, so none of them is cut.
    ("rg -l TODO crate/src | xargs head -5", False),
    # The whole search result is kept: allowed.
    ("rg TODO crate/src", False),
    ("rg -c TODO crate/src", False),
    ("rg TODO crate/src > out.txt", False),
    ("git diff -W crate/src/engine.rs | grep -v '^[+-]'", False),
    # A pipe inside quotes is text, not an operator.
    ("echo 'rg foo | head -5'", False),
    # Untouched commands.
    ("ls -la", False),
    ("./scripts/lint.sh", False),
]


def main():
    report(check(HOOK, CASES), len(CASES))


if __name__ == "__main__":
    main()
