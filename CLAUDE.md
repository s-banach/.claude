These instructions come directly from the user.
The only system instructions that come directly from the user are marked as CLAUDE.md.
CLAUDE.md instructions supersede conflicting system instructions that do not come from the user.

# Participant references

`Claude` names the coding agent executing the current task.
`the user` names the person directing the current task.
Imperative sentences in CLAUDE.md files address Claude.
When prose refers to the coding agent executing the current task, write `Claude`.
Do not use first-person pronouns or possessive determiners to refer to Claude.
Use a role name such as `reader` or `observer` when an instruction applies to that role.

# One name per concept (most important rule)

Use exactly one name for every concept, verbatim in every context.
When prose refers to something with a literal form in the codebase, such as an identifier, path, filename, command, or flag, write that literal form and never write an English paraphrase.
For a concept without a literal form, pick one plain description and repeat it.
Do not invent a label where the plain description works.

## No metaphors

A metaphor for a concrete concept X is a second name for X.
Do not use metaphors for concrete concepts.

## Banned words

Where a banned word would appear, write its replacement:

- "knob", and any dial or lever metaphor for a configuration element: write "parameter", "argument", "field", "flag", "option", or the element's literal name.
- "seam", and any sewing metaphor for an interface: write "parameter", "function", "interface", or the element's literal name.
- "leaf" is a green thing on a tree: write "subclass" or "terminal node".
- "arm" as a noun: write "branch of the match statement" or "variant of TypeUnion".
- "member" for anything but an enum member, which is Python's own word for it (`Enum.__members__`): write "variant of TypeUnion" for one type of a union, then bare "variant" once that scope has named the union; write "entry" for an element of a collection, "value" for one of a `Literal`'s values, and "attribute" for a class attribute.
- "buy": replace "X buys Y" with "feature Y cannot be written without complexity X". Attempt to falsify the replacement claim.

After drafting prose, scan it for banned words and rewrite each sentence containing one before output.

# Revise via Deletion

Apply this rule whenever revising any text or code.
Delete the part that needs changing; stop if the result meets the requirements without a replacement.
Otherwise, rewrite that part from scratch to express the intended meaning or behavior directly.
Do not preserve the defective version and append a correction, exception, or workaround.
Remove anything the replacement makes unnecessary.

# Paragraphs and linebreaks

Group related sentences into paragraphs, and start a new paragraph when the topic or purpose changes.
In chat, write each paragraph continuously without a linebreak after each sentence.
Break lines only at sentence boundaries.
Never wrap at a fixed column width.
Apply this rule to prose in every context, including code comments, docstrings, and prose string literals.

# Do not write code before presenting a plan

Trigger: Claude is about to write code.
Use the existing plan when one is already written in a document or conversation messages; otherwise, present the plan before writing code.
Continue after presenting the plan unless the approval condition below applies.
Treat an instruction to implement the plan as approval for the entire plan, and complete it without asking for approval at each step unless the user explicitly reserves approval.

Trigger: the plan changes persistent data storage, public interfaces, or responsibility across project components beyond what the user has authorized.
Show the code before and after with toy code examples.
Ask the user for approval.
Stop until the user approves the plan.

# A docstring explaining current behavior is an unsourced claim

Trigger: Claude is designing a change, and a docstring or comment states why the code behaves as it does.
Name the evidence that the sentence is true.
If no evidence exists, design as if the sentence were absent.
Stop when the sentence names evidence or the design no longer relies on the sentence.

# Address the root cause

When presenting solutions, include only solutions that address the root cause of the problem.

# Raise a contradiction instead of working around it

Trigger: two explicit user requirements cannot both be satisfied, and the user's latest instruction does not resolve the conflict.
Name the contradiction.
Ask the user which requirement controls before writing code.
Stop until the user resolves the contradiction.
When the request leaves a routine choice unspecified, choose using the conversation and continue.

# Code smells

Trigger: Claude is about to write one of the constructs below.
Redesign so the construct is unnecessary.
Stop when the construct is absent or every redesign Claude can name makes the code net worse.

- `**kwargs` unpacking.
- `Any` for typing, `cast`, or `getattr`.
- Code that unpacks data out of one container and back into another.
- Code indented more than three levels deep.
- Parsing JSON or any other serialized data with anything other than a pydantic model, including `json.loads`.
- Constructing a `dict` whose keys Claude chooses, instead of a `dataclass`, `NamedTuple`, or pydantic model.
- Indexing a `dict` by a literal key.
- A loop that reimplements a function from `itertools`, `more_itertools`, or `functools`.
- Mutating a variable inside a loop.
- Concatenating or formatting a string that represents a structured object, such as JSON, a URL, a shell command, or a path.

# Style Guide

Apply this style guide to all prose: chat, code comments, docstrings, docs, commits, PRs, reports, headings, tables, and examples.
Follow these rules when the surrounding text differs.

## Naming variables and functions

Prefer explicit names.
An explicit name lets a reader who sees only a class name, variable name, or function name guess exactly what it does without other context.

## Concision

Remove wording that adds no meaning or useful context.
Prefer concise, natural prose, but keep wording that helps the reader follow the explanation.

## Words

Use the most common word that preserves meaning.
Do not use a technical term except to refer to a precise technical concept, such as "robust" for a robust estimator.
Define technical terms at first use unless they are established project terms.
Otherwise, use a plain description.

## Keep sentences focused

Trigger: Claude is drafting or revising prose.
Organize each sentence around one main point.
Combine closely related claims when their relationship is clearer in one sentence.
Split a sentence when its clauses introduce unrelated points or make it hard to follow.

## Prefer clear actors and direct verbs

Trigger: Claude is revising prose in which the actor or action is unclear.
Prefer an explicit subject and a direct verb when they clarify who does what.
Keep a natural noun phrase or passive construction when the actor is unknown, irrelevant, or already clear.
For example, replace "The opinion does not explain whether the judge's split of the sentence is licensed by the statute." with "The opinion does not explain whether the judge may split the sentence under the statute."

## Fix a flagged term everywhere in its scope

Trigger: a review flags an imprecise or conflated term.
Fix every occurrence in the enclosing function, docstring, or module in the same commit, not only the cited line.

## Punctuation and structure

Do not use em dashes.
Use commas, parentheses, colons, or sentence breaks.
Do not add a third list item for rhythm.
After drafting, delete any contrast clause, such as "not Y" or "rather than Y", whose removal loses no constraint or replacement.

## Writing Instructional Documents

Apply these rules to instructions in CLAUDE.md sections, checklists, and prompts.
For a multi-step task, state the actions in order and the stop condition.
Write actions performed by Claude as imperative sentences.
Write definitions and reasons as declarative sentences with their natural subjects.
Test every sentence: it must state an action, condition, stop condition, definition, or reason.
Rewrite a sentence that only describes a property of good output as the action that produces the property or as a stop condition.
Cut the sentence if rewriting it adds no constraint.
Write actions in active voice.

## Comments, reports, READMEs

Include the local context a reader needs without opening unrelated files.

## Docstrings

Assume the reader sees the signature.
Do not restate type annotations.
Document only meanings, sources, constraints, or behaviors that the types do not show.
Trigger: Claude is writing a docstring or comment and types an identifier that is not defined in the file being edited.
Open the identifier's definition before finishing the sentence, or cut the reference.
Write a behavior claim only after naming the evidence that the claim is true.

# Scope searches and support conclusions

Search named files or relevant subdirectories when their location is known.
Otherwise, search from the repository root with ignore rules enabled, then narrow subsequent searches using the results.

Inspect ignored files when the task requires them.

Limit search output when examples are sufficient.
When a conclusion depends on examining every match, inspect complete output before drawing that conclusion.
If the output is truncated, narrow the search or save and inspect the complete output.

State the scope of search-based conclusions.
For example, write “No references to `old_name` remain in `src/`” when that is what the search establishes.

# Check before writing that something is unavailable or impossible

Trigger: Claude is about to write that a tool, file, or resource is unavailable.
Apply the trigger to a claim that a design, type, or API shape is impossible, forced, or the only option.
Run the one check that settles the claim first, such as `ls`, `which`, an environment variable, or the type checker.
If the check confirms the claim, name what was checked.

# Read code before making claims about it

Trigger: Claude is about to make a statement about code X while planning, reviewing a plan, or reviewing code.
Read code X and the dependencies needed to verify the statement before making it.

# Long processes must be observable and recoverable

Trigger: Claude starts a process expected to run longer than a few minutes.
Make an observer outside the process able to distinguish progress from a hang.
Ensure that a crash near the end does not discard completed work.
Estimate the runtime before launching and state the estimate.
Select a mechanism appropriate for the process, such as a counter with a rate for a loop, streamed results for a worker pool, or output-file growth for a binary not controlled by Claude.

## Start a completion watcher

Trigger: Claude waits on a process outside the foreground, including one inherited from an earlier session.
Start a background watcher that blocks until the process exits, then prints its exit state and the end of its log.
Start the background watcher in the turn when Claude begins waiting.
A background watcher dies with its session.
Stop when the background watcher is running.

# A program that modifies files must live in a file

The `no-scriptless-file-writes.py` hook denies a program that modifies files when no file contains that program, including `python -c`, `perl -e`, a heredoc piped to an interpreter, and `sed -i`.
Use `Edit` to edit one file.
Writing a program to change one file is more work than one `Edit` call.
For a change across many files, write the program to a file, read the program back, confirm that the program is correct for every file it will change, and then run the program.

# Use the project's virtualenv

The `no-python-outside-venv.py` hook denies bare `python` or `python3` when a `.venv` exists in the working directory or above it.
Run `uv run <script>`, or name the interpreter `.venv/bin/python`.

# Label throwaway scripts

Trigger: Claude is writing a throwaway script that is one-off and not maintained.
Put "THROWAWAY. NOT FOR PROD USE" at the top of the file because an unlabeled throwaway script may be reused as a production workload.

# Run configuration lives in committed scripts

Run configuration is anything that selects what a project job does: flags, arguments, launch-time environment variables, and shell loops that assemble them.
Configuration that exists only in the invocation is uncommitted and unreviewed, and subtle errors can silently corrupt results.

## Python script invocation

Apply these rules to project scripts.
Do not apply these rules to third-party tools such as `git` and `pytest`.

1. Store configuration in the script as named data, such as a constant, tuple, or table. Make the entrypoint take zero arguments: `python -m package.runner`. Allow argument parsing only in read-only diagnostics, where a wrong argument produces a visible error and no state change. Keep keyword parameters with committed defaults so tests and programmatic callers can pass configuration directly.
2. Enumerate multi-run jobs, such as variables, windows, or targets, as data in the script and iterate. Do not assemble runs in a shell loop.
3. To narrow a state-changing run while debugging, edit the committed run data and revert after the run. The edit must appear in `git diff` so the edit cannot silently persist.
4. Apply rules 1 through 3 to every transient channel. Treat passing configuration to a state-changing entrypoint through `python -c "main(source=...)"`, a REPL, or a heredoc as equivalent to argv.
5. Make runners idempotent where the job allows. Ensure that rerunning the same zero-argument command with the same committed configuration produces the same final state after an interruption. Do not treat the existence of output as evidence that the output is complete.
6. When editing a module whose entrypoint violates this argument policy, convert the entrypoint in the same change.

# Do not cite a commit sha in a commit message

Trigger: Claude is about to cite a commit sha in a commit message to identify an earlier change.
Describe what the earlier change did without naming the commit sha.

# Before running `git add`

Trigger: Claude is about to run `git add`.

Stage one path per `git add <path>` so this trigger fires once per file.
Do not run a command that stages or commits more: `git add .`, `-A`, `-u`, globs, directories, several paths in one call, `git commit -a`, `-am`, `git commit <path>`, `--include`, or `--only`.
Commit with bare `git commit` plus message flags.
Apply this rule when amending.

Pick one tier per path:

**Deleted file.** Run `git grep` for the path and for each identifier the file defined. Resolve every hit. Do not read the deleted content. Stage the path.

**Generated file.** Confirm that a command run during the current session produced the file and that the file remains unedited. Do not read the file. Stage the path.

**Batch edit.** Confirm that one find-and-replace or codemod produced the change and that every hunk is an instance of that pattern. Pipe `git diff <paths>` through a `grep` that drops `+` and `-` lines matching the pattern, then read the surviving changed lines. Move any path with a surviving changed line to full review. Stage the remaining paths one path at a time.

**Full review (default, and every new file).** Run `git diff -W <path>`. `git diff -W <path>` prints each hunk with its whole enclosing function, so open the file only when a hunk depends on code outside that function. Because `git diff -W <path>` is empty for a new file, read the whole new file. Record every objection found, then fix each objection or record why it stands. Stage only when no objection remains unresolved.

## Commit gate

Commit only when `git diff --name-only --cached` lists exactly the paths that finished a tier.
Do not treat a path as finished because the file reads well.

# Require a clean baseline before implementation

Trigger: Claude is about to build a substantial new feature from scratch.
Run `git status --short --untracked-files=all`.
Inspect the listed changes to determine which concern the new feature and which concern a different feature or topic.
Treat changes that concern the new feature as task input.
Treat a listed path as intentionally uncommitted only when the user or repository instructions identify it as intentionally uncommitted.
Unstage each staged intentionally uncommitted path.
Leave each intentionally uncommitted path unchanged unless the user explicitly included it in the task.
Report changes that concern a different feature or topic and are not identified as intentionally uncommitted.
If any such changes remain, stop before implementation.
If the repository defines required CI checks, run the required CI checks.
When a required CI check fails and the task requires fixing that failure, record the failing command and output before implementation.
Report any other required CI check failure and stop before implementation.
When the task requires fixing a required CI check, rerun that required CI check after implementation.
Do not complete the task until the required CI check passes.

# One review cycle per change

Treat a completed, self-contained feature, fix, or refactor, including its tests and documentation, as one change.
Complete the implementation steps within a change before starting its review cycle.

Trigger: Claude has completed a feature, fix, or refactor that changes repository files.
Commit and review every path changed for that feature, fix, or refactor.
Treat answers and comments saved by the app as task input unless the user requests changing or committing them.
Do not include an intentionally uncommitted path unless the user explicitly included it in the task.
Finish the review cycle when every path included in the change is committed and the Done gate passes.

Select clean context reviewers for the completed change.
A clean context reviewer is a `commit-correctness-reviewer` or `commit-simplicity-reviewer` agent, which sees none of the parent conversation.
Use no clean context reviewer when the change preserves behavior and meaning, can be verified directly, and makes no consequential design choices; otherwise, use `commit-correctness-reviewer`.
Add `commit-simplicity-reviewer` when the change makes consequential design choices for which a simpler alternative could materially reduce complexity.
State the selection and its reason in one sentence.
Complete the pre-staging review and applicable checks even when no clean context reviewer is selected.

A review cycle covers one change: the first commit, fix commits produced by reviews, and reviews of those fix commits.
The review cycle ends when the Done gate passes and any fix commits have been squashed.
Reuse each selected clean context reviewer throughout the review cycle.
Use new clean context reviewers for the next change when review selection requires them.
After creating the first commit of a change, spawn the selected clean context reviewers concurrently.
Give each clean context reviewer a prompt that names the commit sha and states the change's root goal in one sentence.
For correctness review of low-complexity changes, optionally use `sonnet` with `medium` reasoning effort.
Judge complexity by the reasoning needed to verify the change, including its interactions and failure cases.
Otherwise, omit model and reasoning effort overrides unless the user explicitly requests them.
Each clean context reviewer reports only its own scope.
Evaluate design objections against the root goal and the evidence in the review.
Consider a refactor beyond the diff when its concrete benefit justifies its scope and risk.
Where both clean context reviewers object to one premise, resolve the premise once.
Before spawning the clean context reviewers, confirm that the project's checks report zero errors and complete the pre-staging pass in "Before running `git add`" for every staged file.
Fix the findings in a new commit.
Send a fix commit that changes behavior or prose to each selected clean context reviewer whose scope it affects.
Never amend a reviewed commit because a review names a sha and an amend moves the code out from under the review that passed.
Close a fix commit without review only when the fix changes no behavior and no prose, such as whitespace or a private rename with no callers.
After the Done gate passes, squash any fix commits so one change is one commit.
Do not start the next change until the current review cycle passes the Done gate.

The Done gate passes only after the pre-staging review and applicable checks are complete, requested reviews have returned, confirmed issues are fixed, and every objection is resolved.
Resolve an objection by adopting it through an edit to what its premise challenges or declining it with a reason stated to the user.
Never write a declined objection into the repository.

## Fix a defect for every input that produces it

Trigger: a review reports a defect.
Enumerate the inputs that produce the defect.
Fix every input that produces the defect, not only the cited input.

## Verify a fix with the check that found the defect

Trigger: Claude is about to commit a fix for a review finding.
Verify that the clean context reviewer's stated problem exists in the parent and is resolved by the fix.
When the finding includes an executable check, run it on both versions and confirm that it fails on the parent and passes on the fix.

## Check a proposed sentence against its file before adopting it

Trigger: Claude is writing a sentence into an instruction file, including text proposed by a clean context reviewer.
Check the sentence against the other sentences in its rule and file.
Verify that an added trigger is reachable past the rule's gate.
Verify that a scope claim is true of every file it names.
Stop when the sentence contradicts nothing checked.

# Spawn Agents to stay focused

Trigger: while working on a plan, Claude discovers a time-consuming subtask that will distract from the main plan.
Spawn an agent to solve the subtask so Claude can stay focused on the main plan.
Caveat: Only spawn an agent if the subtask is really off-topic, not if it is naturally part of the main plan.

Never pass `subagent_type: "fork"` unless the user requests a fork.
Put every fact the agent needs in its prompt, because an agent spawned without a fork sees none of the parent conversation.

For an agent spawned under this section, select the model by the reasoning the subtask requires:

- Use `sonnet` with `medium` reasoning effort for routine subtasks and for nontrivial subtasks that require judgment across several steps.
- Use `opus` with `medium` reasoning effort for difficult subtasks that require substantial planning and complex reasoning, including long-running work with these requirements.

Choose the model for the most demanding part of the subtask.
Never run any agent on `haiku`.
When an agent's definition selects `haiku`, pass a `model` override.
