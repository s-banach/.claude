#!/usr/bin/env python3
"""Check no-scriptless-file-writes.py against commands whose verdict is known.

Run `python3 no-scriptless-file-writes-test.py` from this directory after editing the hook.
Each case is (command, denied), where denied is True when the hook must block it.
"""

from pathlib import Path

from hook_testing import check, report

HOOK = str(Path(__file__).with_name("no-scriptless-file-writes.py"))

CASES = [
    # Python program that no file holds, modifying files: denied.
    ("""python -c 'open("log.txt", "w").write("x")'""", True),
    ('''python3 -c "from pathlib import Path; Path('f').write_text('x')"''', True),
    ("""python3 -c 'open("f", "a").write("x")'""", True),
    ("""python3 -c 'open("f", "r+").truncate(0)'""", True),
    ("""python3.12 -c 'Path("f").write_bytes(b"x")'""", True),
    ("""uv run python -c 'import shutil; shutil.move("a", "b")'""", True),
    ("""uv run --with rich python -c 'import os; os.remove("f")'""", True),
    ("""sudo python3 -c 'import os; os.replace("a", "b")'""", True),
    ("""cd /tmp && python -c 'open("f", "w")'""", True),
    ("""/usr/bin/python3 -c 'open("f", "wb").write(b"x")'""", True),
    # Escaped quotes inside a double-quoted shell string.
    ('python3 -c "open(\\"f\\", \\"w\\").write(\\"x\\")"', True),
    # File-modifying program from stdin: denied.
    ("python3 - <<'EOF'\nopen('f', 'w').write('x')\nEOF", True),
    ("python <<EOF\nimport os\nos.rename('a', 'b')\nEOF", True),
    ("uv run python <<EOF\nPath('f').unlink()\nEOF", True),
    ("python3 <<< 'open(\"f\", \"w\")'", True),
    ("echo 'open(\"f\", \"w\").write(\"x\")' | python3", True),
    # `<&0` names a descriptor, not a file holding the program.
    ("echo 'open(\"f\", \"w\").write(\"x\")' | python3 - <&0", True),
    # Python program that no file holds, only computing or printing: allowed.
    ("python -c 'print(1)'", False),
    ('python3 -c "import sys; print(sys.path)"', False),
    ("""python3 -c 'import json; print(json.load(open("data.json")))'""", False),
    ("uv run python -c 'import anthropic'", False),
    ("python3 <<< 'print(1)'", False),
    ("echo 'print(1)' | python3", False),
    ("python", False),
    ("python -u", False),
    ("python3 - <<'EOF'\nprint(1)\nEOF", False),
    # A redirection feeds the program its input, so it does not hold the program.
    ("""python3 -c 'open("f", "w")' < data.txt""", True),
    ("""uv run python -c 'open("f", "w")' < data.txt""", True),
    ("""xargs python3 -c 'open("f", "w")' < files.txt""", True),
    # A file holds the program: allowed even when the command mentions writes.
    ("python script.py", False),
    ("python migrate.py <<EOF\nopen('f', 'w')\nEOF", False),
    ("python < script.py", False),
    ("""echo 'open("f", "w")' > gen.py; python3 - < gen.py""", False),
    ("perl -i - < fix.pl notes.txt", False),
    ("python3 -m pytest", False),
    ("uv run python -m pkg.runner", False),
    # A module name attached to `-m` leaves no positional argument, and can
    # reach a letter that means program text: `cProfile` holds a `c`.
    ("""echo 'open("f", "w")' > gen.py; python3 -mpytest""", False),
    ("""echo 'open("f", "w")' > gen.py; python3 -mcProfile gen.py""", False),
    ("""echo 'open("f", "w")' > gen.py; python3 -mjson.tool""", False),
    ("uv run scripts/migrate.py", False),
    # Print-and-exit flags: allowed.
    ("python --version", False),
    ("python3 -V", False),
    # Perl, in place or writing from a program no file holds: denied.
    ("""perl -pi -e 's/a/b/g' src/foo.py""", True),
    ("""perl -i -pe 's/a/b/' src/foo.py""", True),
    ("""perl -i.bak -pe 's/a/b/' src/foo.py""", True),
    ("""perl -e 'open(FH, ">", "f"); print FH "x"'""", True),
    ("""perl -e 'open(OUT, ">>out.log")'""", True),
    # Perl that only prints, and perl whose program is in a file: allowed.
    ("""perl -pe 's/a/b/' src/foo.py""", False),
    ("""perl -MTime::HiRes -e 'print 1'""", False),
    ("""perl -MFile::Find -e 'find(sub { print }, ".")'""", False),
    ("perl script.pl", False),
    # `-m` means "run this installed module" only for python.
    ("""perl -m Foo -e 'open(F, ">x")'""", True),
    ("""perl -mFoo -e 'open(F, ">x")'""", True),
    # Ruby.
    ("""ruby -e 'File.write("f", "x")'""", True),
    ("""ruby -i -pe 'gsub(/a/, "b")' src/foo.rb""", True),
    ("""ruby -e 'puts 1'""", False),
    ("ruby script.rb", False),
    # Node.
    ("""node -e 'require("fs").writeFileSync("f", "x")'""", True),
    ("""node --eval 'fs.appendFileSync("f", "x")'""", True),
    ("""node -e 'console.log(1)'""", False),
    ("node build.js", False),
    # Stream editors rewriting a file with a program no file holds: denied.
    ("""sed -i '' 's/a/b/' src/foo.py""", True),
    ("""sed -i.bak 's/a/b/' src/foo.py""", True),
    ("""sed --in-place 's/a/b/' src/foo.py""", True),
    ("""gawk -i inplace '{print}' src/foo.txt""", True),
    # Stream editors that print, or whose program is in a file: allowed.
    ("""sed 's/a/b/' src/foo.py""", False),
    ("""sed -n '1,5p' src/foo.py""", False),
    ("""sed -i -f fix.sed src/foo.py""", False),
    ("""awk '{print $1}' src/foo.txt""", False),
    ("awk -f prog.awk src/foo.txt", False),
    ("""sed --file=fix.sed -i src/foo.py""", False),
    # A long option holding an `i` is not an in-place flag.
    ("sed --version", False),
    ("awk --version", False),
    ("""sed --expression='s/a/b/' src/foo.py""", False),
    ("""sed --silent '1,5p' src/foo.py""", False),
    ("""awk --field-separator=, '{print $1}' data.csv""", False),
    ("""awk --posix '{print}' src/foo.txt""", False),
    # Line editors: denied, their program never lives in a file.
    ("ed src/foo.py <<EOF\ns/a/b/\nw\nEOF", True),
    ("""ex -c 'wq' src/foo.py""", True),
    # Untouched commands, with and without a write pattern.
    ("echo \"open('f', 'w')\" > snippet.py", False),
    ("pythonista -c 'open(\"f\", \"w\")'", False),
    ("uv run pytest", False),
    ("which python", False),
    ("echo 'python -c is banned'", False),
    ("git log --oneline", False),
    ("grep -c pattern file.py", False),
    ("rsync -ai src/ dst/", False),
    # `env` hands the command that follows it to the interpreter behind it.
    ("""env python3 -c 'open("f", "w").write("x")'""", True),
    ("""env PYTHONPATH=. python3 -c 'open("f", "w")'""", True),
    ("env python3 script.py", False),
]


def main():
    report(check(HOOK, CASES), len(CASES))


if __name__ == "__main__":
    main()
