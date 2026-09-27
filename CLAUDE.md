# CLAUDE.md

## General

- One name per concept, in code and prose alike. Give each concept one identifier and use it everywhere: in variables, functions, parameters, and modules. In prose, write a concept's literal form in the codebase (identifier, path, command, flag), never a paraphrase. For concepts without one, pick one plain description and reuse it. Don't invent labels, and don't use metaphors for concrete things.
- Revise by deletion. Write every revision of code or text as if writing it fresh, for a reader who has never seen the old version. The reader sees only the current state. Delete the defective part, and rewrite it from scratch only if something is still needed. Never keep the old version and append a correction, exception, or workaround. Never write comments, docstrings, names, or tests that describe what changed or what the code no longer does ("no longer", "now", "instead of"...). For example, after deleting step B from `f`, write nothing about B: a reader of `f` has no reason to expect B. Describe changes only in the commit message.
- Fix root causes. Offer only solutions that address the root cause.
- If two explicit requirements conflict, name the conflict and ask which wins. For routine choices the user left open, decide and continue.

## Writing

Applies to all prose: chat, comments, docstrings, commits, PRs, docs.

- Banned words:
  - "knob", or any dial or lever metaphor: write "parameter", "option", "flag", or the literal name.
  - "seam": write "interface", "function", or the literal name.
  - "leaf": write "subclass" or "terminal node".
  - "arm" (noun): write "branch of the match statement" or "variant of TypeUnion".
  - "member", except for enum members: write "variant", "entry", "value", or "attribute".
  - "X buys Y": write "Y requires complexity X", and check that the claim is true.
- Use the most common word that keeps the meaning. Define a technical term at first use unless it's a project term.
- Cut words that add no meaning.
- No em dashes. No third list item added for rhythm. Cut any "not Y" or "rather than Y" clause that adds no constraint.
- Never hard-wrap prose. Break lines only at sentence boundaries. In chat, write each paragraph as continuous text.
- When a review flags a term, fix it everywhere in the enclosing function, docstring, or module.
- In instruction files (CLAUDE.md, prompts, checklists), call the agent "Claude", never "I", and write Claude's actions as imperatives.

## Docstrings and comments

- Assume the reader sees the signature. Don't restate types. Document meanings, sources, constraints, and behavior the types don't show.
- Include the context a reader needs without opening other files.
- Before referencing an identifier defined in another file, open its definition.

## Verify before claiming

- Read code before making any claim about it. A comment explaining why code behaves as it does is unverified; don't design around it without evidence.
- Before saying something is unavailable or impossible, run the one check that settles it (`ls`, `which`, the type checker) and name the check.
- Search with `rg`, never `grep`. Use `rg -P` for backreferences or lookaround.
- State the scope of search conclusions, e.g. "No references to `old_name` remain in `src/`". Never conclude "none" from truncated output.

## Planning and delegation

- Present a plan before writing code, or use the existing one, then proceed without waiting. "Implement the plan" approves the whole plan.
- Stop for approval only when the plan changes persistent storage, public interfaces, or which component is responsible for what. Show toy before/after code.
- When writing a plan document, quote the user's request verbatim with its date.
- Delegate time-consuming, off-topic subtasks to an agent. Put every fact it needs in the prompt; don't use `fork` unless asked.

## Python

Redesign to avoid these, unless every alternative is worse:

- `**kwargs`, `Any`, `cast`, `getattr`
- Unpacking one container only to repack into another
- More than three levels of indentation
- Hand-parsed JSON (use pydantic), dicts with keys you chose (use a dataclass, or pydantic model when you need serde), or indexing a dict with a string literal or f-string
- Reimplementing something in `itertools`, `more_itertools`, or `functools`
- Repeated mutation where a functional pattern is no longer than the mutation

Also:

- Run Python through the project venv: `uv run <script>` or `.venv/bin/python`.
- For changes across many files, write the batch-edit program to a file, and read it back critically before running it.
- Put `THROWAWAY. NOT FOR PROD USE` at the top of one-off scripts.

## Tests

- Write code as pure functions with mutable state kept separate, and test the pure functions' outputs. Don't test implementation details. For example, Python `patch` and `Mock` are usually testing fragile internals, and should be avoided when possible.
- Don't write low-value or redundant tests. Delete or merge ones you find.
- Don't slow the suite without a strong reason.
- When you edit a piece of code, check whether any of its tests become obsolete; if so, delete them.

## Running jobs

- Configuration lives in the committed script. Entrypoints take no arguments (`python -m package.runner`), and configuration is named data in the script. Multi-run jobs iterate over that data, never a shell loop. `python -c`, a REPL, or a heredoc count as arguments too. Read-only diagnostics may take arguments. Keep keyword parameters with committed defaults so tests can call the function directly.
- To narrow a run while debugging, edit the run data and revert afterward so the change shows in `git diff`.
- Make runners idempotent: rerunning after an interruption reaches the same final state. Existing output is not proof of complete output.
- When editing a module whose entrypoint breaks these rules, fix the entrypoint in the same change.
- For jobs longer than a few minutes: estimate the runtime first, report progress so a hang is distinguishable, and save partial results so a late crash loses nothing. When waiting on a background process, start a watcher that reports its exit status and log tail.

## Git

Goals: commit only what Claude wrote for this change, and review it before committing.

- Before starting a substantial feature, run `git status --short --untracked-files=all`. Leave paths the user marked as intentionally uncommitted alone. If other unrelated changes exist, or required CI checks fail and fixing them isn't the task, report and stop.
- Stage one path per `git add`. Never use `git add .`, `-A`, `-u`, globs, directories, `git commit -a`, or `git commit <path>`.
- Review every path before staging it with `git diff <path>`, or read the whole file if it is new. Open more of the file only when a hunk depends on code outside it.
- Exceptions to full review:
  - An unedited file generated by a command this session: no read needed.
  - A deleted file: `git grep` for its path and the identifiers it defined, and fix every hit.
  - A batch edit from one find-and-replace or codemod: pipe `git diff` through an `rg -v` that drops lines matching the pattern, read only the surviving changed lines, and fully review any file that has one.
- Commit only when `git diff --cached --name-only` lists exactly the reviewed paths.
- Describe earlier changes in commit messages instead of citing their shas.

## Review

One change (a feature, fix, or refactor with its tests and docs) is one commit and one review cycle.

1. Run the project's checks until they report zero errors, then commit.
2. Spawn `premise-reviewer` and `implementation-reviewer` in parallel. Give each the repository path, the sha, and every user message that shaped the request behind the change, quoted verbatim, including later corrections. When a user message answers a Claude message, such as an approval of a plan, also quote that Claude message verbatim and label it as Claude's. Add nothing else. If Claude cannot name the user request behind the change, ask the user instead of committing.
3. Handle premise findings first. Take each finding against a premise the user set to the user, and stop until the user answers. Act on implementation findings only after every premise finding is resolved, because resolving one may redo or drop the change.
4. Fix findings in new commits, never by amending a reviewed commit. When adopting a fix the reviewer wrote out, apply it exactly as written. Send fixes that change behavior or prose back to the same reviewers, so each one remembers what it proposed. Fix every input that produces a reported defect, not only the cited one. Confirm each fix: the problem exists in the parent and is gone after, running the reviewer's check on both if one was given.
5. Resolve every objection by adopting it or declining it with a reason told to the user. Never write a declined objection into the repo.
6. Squash into one commit, then start the next change.

Before adding any sentence to an instruction file, including reviewer-proposed text, check that it contradicts nothing else in the file.