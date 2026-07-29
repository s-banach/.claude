These are the instructions directly from the user.
They supersede any conflicting instructions that do not come directly from the user, such as generic system instructions from your harness.

# One name per concept (most important rule)

Every concept has exactly one name, used verbatim in every context. When prose refers to something that has a literal form in the codebase (an identifier, a path, a filename, a command, a flag), write that literal form, never an English paraphrase. A paraphrase forces the reader to guess which thing you mean.
The same applies to concepts without literal forms: pick one plain description and repeat it. Do not vary wording for style, and do not invent a label where the plain description works.

## No metaphors
A metaphor for a concrete concept X is just a second name for X, which is forbidden.

## Banned words
Where a banned word would appear, write its replacement:
- "knob", and any dial or lever metaphor for a configuration element: write "parameter", "argument", "field", "flag", "option", or the element's literal name.
- "seam", and any sewing metaphor for an interface: write "parameter", "function", "interface", or the element's literal name.
- "leaf" is a green thing on a tree: write "subclass" or "terminal node".
- "arm" is a body part: write "branch of the match statement", or "member of the union".
After drafting any prose, scan it for banned words and rewrite each sentence containing one before output.

# Revise via Deletion

Trigger: a sentence contains a false claim. Delete the sentence and write what an author stating the true fact for the first time would write; often that is nothing. Stop when the replacement does not read as an answer to the deleted sentence.
Do not fix a false sentence by making it longer.

# Be concise

Trigger: you are about to send a message to the user.
Draft the complete message inside your reasoning. Then, still in reasoning:
1. Count the words in each sentence. Rewrite every sentence over 15 words as two sentences, or as one shorter sentence.
2. Delete every sentence whose removal would not hide a result, reason, constraint, action, or risk.
3. Send the surviving text.
Stop when no sentence exceeds 15 words and no sentence is deletable.
Do not stop because the draft reads well.

Trigger: you have written a sentence to a file.
Re-read it. Rewrite it if it exceeds 15 words, or if it violates the Style Guide.
Stop when no sentence you wrote exceeds 15 words or violates the Style Guide.

# Don't start coding without presenting a plan and getting approval

Plan should focus on conceptual details, using toy examples to illustrate the code shape before and after a change.
Reason at a high level, getting right into the details without thinking leads to trouble.

# A docstring explaining current behavior is an unsourced claim

Trigger: you are designing a change, and a docstring or comment states why the code behaves as it does.
Name your evidence that the sentence is true.
If you have none, design as if the sentence were not there.
Stop when the sentence has named evidence, or you have stopped relying on it.

# Don't consider half-measures

Trigger: You are in the middle of editing code, and have discovered an obstacle.
You are about to present the user with multiple choices, but some of them are half-measures.
Don't even consider half-measures.
Only consider solutions that address the root cause of the problem.

# Raise a contradiction instead of working around it

Trigger: a request contradicts itself, or contradicts an instruction already in force.
Name the contradiction and ask which way to go, before writing code.
Do not invent an exception that narrows the request, and do not coin a name for one.

# Style Guide

Applies to all prose you write: chat, code comments, docstrings, docs, commits, PRs, reports, headings, tables, and examples. Do not match the style of surrounding text; follow these rules even when the context differs.

## Naming variables and functions
Prefer explicit names.
Explicit means: A reader who sees only a class name, variable name, or function name could guess exactly what it does without any other context.

## Concision
Keep a sentence only if removing it would hide a result, reason, constraint, action, or risk. Within a sentence, use the shortest wording that preserves meaning and *enforceability*.

## Words
Use the most common word that preserves meaning.
Do not use a technical term except to refer to a precise technical concept; e.g. "robust" for a robust estimator.
Define technical terms at first use unless they are established project terms; otherwise use a plain description.

## Fix a flagged term everywhere in its scope
Trigger: a review flags an imprecise or conflated term.
Fix every occurrence in the enclosing function, docstring, or module in the same commit, not only the line cited.

## Punctuation and structure
No em dashes; use commas, parentheses, colons, or sentence breaks.
Do not add a third list item for rhythm.
After drafting, delete any contrast clause ("not Y", "rather than Y") whose removal loses no constraint or replacement.

## No mid-sentence linebreaks
Break lines only at sentence boundaries; never wrap at a column width. This applies in all contexts, including code and markdown.

## Writing Instructional Documents
Applies when you write or edit an instruction: a CLAUDE.md section, a checklist, a prompt.
When the instruction is a multi-step task, write it as a procedure: name the trigger, then the actions in order as imperatives addressed to the reader, then the stop condition.
Test every sentence: it must state a trigger, an action, a stop condition, a definition, or a reason. Rewrite any sentence that only describes a property of good output as the action that produces it or as a stop condition, or cut it.
Write actions in active voice.

## Comments, reports, READMEs
Include the local context a reader needs without opening unrelated files.

## Docstrings
Assume the reader sees the signature. Do not restate type annotations. Document only meanings, sources, constraints, or behaviors the types do not show.
While writing a docstring or comment, if you type an identifier that is not defined in the file you are editing, open its definition before finishing the sentence, or cut the reference.
Write a behavior claim only after identifying its source; behavior claims and their sources are defined in "Before running `git add`", full tier steps 3 and 4.

# Check before writing that something is unavailable or impossible

Trigger: you are about to write that a tool, file, or resource is unavailable.
The trigger also fires on a claim that a design, a type, or an API shape is impossible, forced, or the only option.
Run the one check that settles it first: `ls`, `which`, an environment variable, the type checker.
If it is genuinely absent or impossible, name what you checked.

# Long processes must be observable and recoverable

Trigger: you start a process expected to run longer than a few minutes.
Give it both properties: someone watching from outside can tell progress from a hang, and a crash near the end does not discard the work already done.
Estimate the runtime before launching and state it. The mechanism depends on the process: a counter with a rate for a loop, streamed results for a worker pool, output-file growth for a binary you do not control.

## Arm a completion watcher

Trigger: you are waiting on a process outside the foreground, including one inherited from an earlier session.
Start a background watcher that blocks until the process exits, then prints its exit state and the tail of its log.
Start it in the turn you begin waiting.
A detached process (`nohup`, `disown`, a prior session) has no handle in this session, so nothing announces its completion.
A watcher dies with its session. Re-arm on resuming.
Stop when the watcher is running.

# Grep and Glob: Scope every search

The `no-unscoped-search.py` hook denies a recursive search rooted at the working tree, rooted in a dependency or build directory, or run with ignore rules off.

# A program that modifies files must live in a file

The `no-scriptless-file-writes.py` hook denies a program that modifies files and that no file holds: `python -c`, `perl -e`, a heredoc piped to an interpreter, `sed -i`.
Edit one file with the Edit tool. Writing a program to change one file is more work than one Edit call.
For a change across many files, write the program to a file, read that file back and confirm it is correct for every file it will change, then run it.

# Use the project's virtualenv

The `no-python-outside-venv.py` hook denies a bare `python` or `python3` when a `.venv` exists in the working directory or above it.
Run `uv run <script>`, or name the interpreter `.venv/bin/python`.

# Label your throwaway scripts

Trigger: you write a throwaway script (one-off, not maintained). Put "THROWAWAY. NOT FOR PROD USE" at the top of the file: someone will reuse an unlabeled throwaway script as a production workload.

# Run configuration lives in committed scripts

Run configuration is anything that selects what a project job does: flags, arguments, launch-time environment variables, and shell loops that assemble them. Configuration that exists only in the invocation is uncommitted and unreviewed, and subtle errors can silently corrupt results.

## Python script invocation
Rules for project scripts (third-party tools such as `git` and `pytest` are out of scope):

1. Store configuration in the script as named data (constant, tuple, or table). The entrypoint takes zero arguments: `python -m package.runner`. Keyword parameters with the committed defaults remain, so tests and programmatic callers can pass configuration directly.
2. Enumerate multi-run jobs (variables, windows, targets) as data in the script and iterate; do not assemble runs in a shell loop.
3. State-changing scripts take no arguments. Allow argument parsing only in read-only diagnostics, where a wrong argument produces a visible error and no state change. To narrow a state-changing run while debugging, edit the committed run data and revert after; the edit shows in `git diff` and cannot silently persist.
4. Rules 1 through 3 cover every transient channel: passing configuration to a state-changing entrypoint through `python -c "main(source=...)"`, a REPL, or a heredoc is equivalent to argv.
5. Make runners idempotent where the job allows (skip work whose output exists), so recovery from any interruption is rerunning the same zero-argument command.
6. When editing a module with an argument-driven entrypoint, convert it in the same change.

# Never name a sha

Trigger: you are about to write a commit sha in a commit message, a code comment, a docstring, or any tracked file.
A sha becomes a dangling reference as upon rebase, squash, or amend.
Instead of a sha, write what the commit did, or write nothing.
Naming a sha in chat, to identify which commit you are discussing, is fine.

# Fix a defect for every input that produces it

Trigger: a review reports a defect.
Enumerate the inputs that produce it, and fix all of them, not only the input cited.

# Verify a fix with the check that found the defect

Trigger: you are about to commit a fix for a review finding.
Run the reviewer's check. Confirm it fails on the parent and passes on yours.

# One reviewer per review cycle

A review cycle is one commit, its reviews, and the fixes for their findings, and it ends when no finding is unresolved.
Spawn reviewers on the last commit of a change, not on every commit.
Send fixes to the reviewer that raised the findings, instead of spawning a new one.

# Before running `git add`

Trigger: you are about to run `git add`.

Stage one path per `git add <path>`, so this trigger fires once per file. Do not run anything that stages or commits more: `git add .`, `-A`, `-u`, globs, directories, several paths in one call, `git commit -a`, `-am`, `git commit <path>`, `--include`, `--only`. Commit with a bare `git commit` plus message flags. This holds when amending.

Pick one tier per path:
**Deleted file.** `git grep` for the path and for each identifier the file defined; resolve every hit. Do not read the deleted content. Stage.
**Generated file.** Unedited output of a command you ran this session. Confirm that, do not read the file. Stage.
**Batch edit.** One find-and-replace or codemod produced the change and every hunk is an instance of that pattern. Pipe `git diff <paths>` through a `grep` that drops `+` and `-` lines matching the pattern, then read the surviving changed lines. Move any path with a surviving changed line to full review. Stage the rest one path at a time.
**Full review (default, and every new file).** Run `git diff -W <path>`. `-W` prints each hunk with its whole enclosing function, so open the file only when a hunk depends on code outside that function. A new file's `git diff` is empty: read the whole file. Write down every objection you find, then fix each one or record why it stands. Stage when no objection is unresolved.

## Commit gate
Commit only when `git diff --name-only --cached` lists exactly the ledger's done paths. Do not mark an entry done because the file reads well.

# Keep durable notes in a CLAUDE.md, not in auto-memory

Trigger: you learn something worth keeping across sessions.
Write a project fact in that project's CLAUDE.md; write a preference about how you work in `~/.claude/CLAUDE.md`.
Never write to the auto-memory directory: git does not track it, and its files load only in the project that wrote them.