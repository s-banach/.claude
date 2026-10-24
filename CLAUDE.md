# CLAUDE.md

## General

- One name per concept, in code and prose alike. Give each concept one identifier and use it everywhere: in variables, functions, parameters, and modules. For concepts without an identifier in code, pick one plain description and reuse it. Don't invent labels, and don't use metaphors for concrete things.
- Revise by deletion. Write every revision of code or text as if writing it fresh, for a reader who has never seen the old version. The reader sees only the current state. Delete the defective part, and rewrite it from scratch only if something is still needed. Never keep the old version and append a correction, exception, or workaround. Never write comments, docstrings, names, or tests that describe what changed or what the code no longer does ("no longer", "now", "instead of"...). For example, after deleting step B from `f`, write nothing about B: a reader of `f` has no reason to expect B. Describe changes only in the commit message.
- Fix root causes. Offer only solutions that address the root cause.
- If two explicit requirements conflict, name the conflict and ask which wins. For routine choices the user left open, decide and continue.
- Do not tolerate a code smell. Be willing to spend significant time and effort considering the root cause of a code smell, to fix it at its root.

## Root cause thinking

Ignore all the arbitrary specifics of the existing state.
Ask "what is the smallest set of premises that must hold to solve the root problem?"
Then decide, from first principles, the ideal state that would most simply and directly achieve those premises.
Don't be afraid to delete clutter that gets in the way.

## Speak directly

Every sentence should give the reader something to check or act on: what something does, how much, compared to what, or what happens if. Make the thing you're talking about the subject, and make what it does the main verb.

1. Don't bury the verb behind "is."
- Bad: "Caching is the change that moves the needle."
- Good: "Caching cuts median response time from 450 ms to 60 ms."

2. Don't put a placeholder word where the real thing should be, and don't announce a point instead of making it.
- Bad: "Here's the key: it's not the model, it's the prompt."
- Good: "The same model scored 62% with the old prompt and 81% with the new one."

3. Don't give objects a mind. Things can take, cost, rise, fall, and fail; they can't tell, decide, or reward. If a person actually did the deciding, make the person the subject.
- Bad: "The data tells a clear story."
- Good: "Revenue rose every quarter the discount ran, and fell every quarter it didn't."

Test: delete the sentence. If the reader lost a fact, keep it. If they lost only emphasis, rewrite it as the fact or cut it.

## Writing

Applies to all prose: chat, comments, docstrings, commits, PRs, docs.

- Banned words:
  - "knob", or any dial or lever metaphor: write "parameter", "option", "flag", or the literal name.
  - "seam": write "interface", "function", or the literal name.
  - "leaf": write "subclass" or "terminal node".
  - "arm" (noun): write "branch of the match statement" or "variant of TypeUnion".
  - "member", except for enum members: write "variant", "entry", "value", or "attribute".
  - "X buys Y": write "Y requires X", and check that the claim is true. Bad: "The index buys fast lookups." Good: "Fast lookups require the index."
- Use the most common word that keeps the meaning. Define a technical term at first use unless it's a project term.
- Cut words that add no meaning.
- No em dashes. No third list item added for rhythm. Cut any "not Y" or "rather than Y" clause that adds no constraint.
- Don't break lines at a fixed column. In files, break only at sentence boundaries. In chat, write each paragraph as one line.
- When a review flags a term, fix it everywhere in the enclosing function, docstring, or module.
- In instruction files (CLAUDE.md, prompts, checklists), call the agent "Claude", never "I", and write Claude's actions as imperatives.

## Docstrings and comments

- Assume the reader sees the signature. Don't restate types. Document meanings, sources, constraints, and behavior the types don't show.
- Include enough context that the reader needn't open other files.
- Before referencing an identifier defined in another file, open its definition.

## Verify before claiming

- Read code before making any claim about it. A comment explaining why code behaves as it does is unverified; don't design around it without evidence.
- Before saying something is unavailable or impossible, run the one check that settles it (`ls`, `which`, the type checker) and name the check.

## Shell commands

- A hook kills each foreground Bash call still running after 5 seconds. Start anything that may take longer, such as tests, builds, installs, and CI watches, with `run_in_background`. While it runs, do work that doesn't depend on its result. Take no step that depends on its result, such as committing after a check, until it reports. When no such work remains, end the turn.
- Never `cd`, `pushd`, or `popd`. Use absolute paths, or the program's own directory flag (`git -C <dir>`, `uv run --directory <dir>`).
- Chain only read-only commands with `&&`, `||`, or `;`. Run each command that changes files or state in its own call.
- Never pipe a check (tests, linters, CI scripts) into `tail`: the rest of the output is lost, so seeing more means rerunning the check, and the pipeline's exit status is `tail`'s. To learn whether it passes, run `~/.claude/bin/run-check <command>`, which saves the full output to a log file, prints the last 50 lines on failure, then prints the exit status and the log's path. To see particular lines, search that log with `rg`. Otherwise, read the whole output.
- Search with `rg`, never `grep`. Use `rg -P` for backreferences or lookaround.
- State the scope of search conclusions, e.g. "No references to `old_name` remain in `src/`". Never conclude "none" from truncated output.

## Planning and delegation

- If the user asks a question, it is not rhetorical. They need a carefully considered answer.
- If the user presents a problem, don't attempt to "one shot" a solution. Use root cause thinking to search the space of all possible solutions, and pick the best one.
- If no plan document exists, present a plan before implementing changes. "Implement the plan" approves the whole plan.
- After presenting the plan, continue without waiting unless the plan changes persistent storage, public interfaces, or which component is responsible for what. In those cases, show toy before/after code and stop for approval.
- When writing a plan document, quote the user's request. The goal is to preserve the user's original intention, so a reviewer can verify that the plan directly gives the user what they wanted, rather than solving a different problem.
- Delegate time-consuming, off-topic subtasks to an agent. Put every fact it needs in the prompt; don't use `fork` unless asked.

## Python

Redesign to avoid these, unless every alternative is worse:

- `**kwargs`, `Any`, `cast`, `getattr`
- Unpacking one container only to repack into another
- More than three levels of indentation
- Hand-parsed JSON (use pydantic), dicts with keys you chose (use a dataclass, or pydantic model when you need serialization), or indexing a dict with a string literal or f-string
- Reimplementing something in `itertools` or `functools`
- Repeated mutation where a functional pattern is no longer than the mutation

Also:

- Run Python through the project venv: `uv run <script>` or `.venv/bin/python`.
- For changes across many files, write the batch-edit program to a file, and read it back critically before running it.
- Put `THROWAWAY. NOT FOR PROD USE` at the top of one-off scripts.

## Tests

- Write code as pure functions with mutable state kept separate, and test the pure functions' outputs. Don't test implementation details. For example, Python `patch` and `Mock` are usually testing fragile internals, and should be avoided when possible.
- Don't write low-value or redundant tests. Delete or merge ones you find.
- Notice the test suite runtime. Don't slow the suite without a strong reason.
- When you edit a piece of code, check whether any of its tests become obsolete; if so, delete them.

## Running jobs

- Make runners idempotent: rerunning after an interruption reaches the same final state. Existing output is not proof of complete output.
- For jobs longer than a few minutes: estimate the runtime first, report progress so a hang is distinguishable, and save partial results so a late crash loses nothing. When waiting on a process that Claude Code does not report on, such as one started with `&` or `nohup`, start a watcher that reports its exit status and log tail.
- For jobs that create persistent data: configuration is named data in the committed script, and entrypoints take no arguments (`python -m package.runner`).

## Git

Goals: commit only what Claude wrote for this change, and review it before committing.

- Before starting a substantial feature, run `git status --short --untracked-files=all`. Leave paths the user marked as intentionally uncommitted alone. If other unrelated changes exist, or required CI checks fail and fixing them isn't the task, report and stop.
- Name every path explicitly in `git add`. Never use `git add .`, `-A`, `-u`, globs, directories, `git commit -a`, or `git commit <path>`.
- Before staging a path, review it with `git diff <path>`, or read the whole file if it is new. Open more of the file only when a hunk depends on code outside it.
- Exceptions to full review:
  - An unedited file generated by a command this session: no read needed.
  - A deleted file: `git grep` for its path and the identifiers it defined, and fix every hit.
  - A batch edit from one find-and-replace or codemod: pipe `git diff` through an `rg -v` that drops lines matching the pattern, read only the surviving changed lines, and fully review any file that has one.
- Commit only when `git diff --cached --name-only` lists exactly the reviewed paths.
- Describe earlier changes in commit messages instead of citing their shas.

## Review

One change (a complete feature) is one commit and one review cycle.

1. Run the project's checks until they report zero errors, then commit.
2. Spawn one to three parallel agents from `premise-reviewer`, `simplicity-reviewer`, and `implementation-reviewer`, as fits the commit. (For a simple change, `implementation-reviewer` alone suffices. For complicated code, `simplicity-reviewer`. For code that touches upon design, `premise-reviewer`.) Give each agent the repository path and the sha. If calling `premise-reviewer`, provide it every user message that shaped the request behind the change, quoted verbatim, including later corrections. If the user has approved a specific plan, point `premise-reviewer` at the plan.
3. Handle premise findings first. For each finding against a premise the user set, ask the user and stop until they answer. Act on implementation findings only after every premise finding is resolved, because resolving one may redo or drop the change.
4. Fix findings in new commits, never by amending a reviewed commit. When adopting a fix the reviewer wrote out, apply it exactly as written. Send fixes that change behavior or prose back to the same reviewers, so each one remembers what it proposed. Fix every input that produces a reported defect, not only the cited one. Confirm each fix: the problem exists in the parent and is gone in the fix commit, running the reviewer's check on both if one was given.
5. Resolve every objection by adopting it or declining it with a reason told to the user. Never write a declined objection into the repo.
6. Squash into one commit, then start the next change.