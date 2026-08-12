# Dirty-tree triage (SKILL.md Step 1e.2a → 1e.4)

Read this when SKILL.md Step 1e.2a routes here: dirt remains that neither the keep-dirty reload nor the interrupted-phase test explained. A clean-tree run never needs it.

Uncommitted changes at run start are not all the same thing. Some are the work's **input**: domain docs, ADRs, a design note — produced by the planning that informs the plan, reaching the run uncommitted by construction. They belong in their own commit ahead of Phase 1, because folding them into a phase commit misattributes them. Everything else must simply be left alone. The orchestrator cannot tell which is which by looking — the same path is an input in one repo and drift in the next — so it asks.

**Two rules govern everything here.** A dirty tree never stops the run: it is resolved by asking. And **no file ever leaves the working tree** — no `git reset`, no `git checkout --`, no `rm`, no `git stash`. A path is either committed as an input or left exactly as found.

## Step 1 — List the paths

```bash
git -c core.quotePath=false status --porcelain -uall
```

Both flags matter. `-uall` stops git collapsing an untracked directory into a single `?? docs/adr/` entry — without it the user disposes of files they were never shown, and a later `git add -- docs/adr/` would stage everything underneath. `core.quotePath=false` prevents escaping of non-ASCII bytes.

**Unquote before using any path in a git command.** Porcelain still C-quotes a path containing a space, `"`, `\`, or a control character — `core.quotePath=false` does not prevent that. Such a line looks like `?? "docs/design draft.md"`. Strip the surrounding double quotes and unescape `\"` and `\\` before the path reaches `git add` or a `':(exclude)…'` pathspec. This is not cosmetic: `':(exclude)"docs/design draft.md"'` **exits 0 and stages the file anyway**, so a keep-dirty path with a space in its name would be silently committed.

**A rename entry is one item, two paths.** `R  old.md -> new.md` lists as a single numbered item, but every command that later touches it — `git restore --staged`, `git add`, an `':(exclude)'` entry — must name BOTH paths, or the un-named half stays in the index and reaches a phase commit alone (a keep-dirty rename handled by `new.md` only would still commit the deletion of `old.md`).

Disregard keep-dirty entries already recorded — reloaded from a prior run's `tree-state.md` in Step 1e.2, or recorded earlier this run. On a truly first pass none exist.

**Omit `<plan_file_path>` from the list.** The plan file is the run's own record: Step 4.6 edits it and Step 4.7 commits it every phase, so it can never be keep-dirty — excluding it would strand every checkbox edit outside the commit record and arm the next resume's interrupted-phase correction against genuinely completed phases. Pre-existing dirt in it simply rides the run's normal staging. If the omissions leave nothing to list, record nothing and return to SKILL.md Step 1e.3 — there is no one to ask about an empty list.

## Step 2 — Ask

```
Working tree has uncommitted changes. Which are this work's input — to be
committed on their own before Phase 1?

  1.  M   docs/CONTEXT.md
  2.  ??  docs/adr/0007-session-boundary.md
  3.  M   AGENTS.md

Reply with the numbers (e.g. "1,2"), "all", or "none".
Anything you don't name is left exactly as it is and kept out of every commit
this run makes. Reply "stop" if you'd rather handle these yourself first.
```

Present the numbered list exactly once and keep those numbers fixed for the whole exchange — never renumber on a re-prompt, since the numbers are the addressing scheme and a renumbered list silently redirects the user's answer to a different file.

**Never infer which paths are inputs from their names or contents.** If the invocation already said ("commit the doc updates, leave AGENTS.md alone"), map that onto the numbers and show it as the pre-filled answer — then let the user confirm, correct, or override it. The same goes for `input:` entries a prior run recorded in `tree-state.md` whose commit never landed: pre-fill, never auto-apply. Mapping prose onto paths is inference, and an unconfirmed guess commits files the user never named.

**Reply handling** — every case has one outcome:

- **Numbers, `all`, or `none`** → apply Step 3.
- **A confirmation of a pre-filled answer** (`yes`, `ok`, `that's right`) → apply that answer. A non-reply is never confirmation: an empty or absent answer routes through the last case below.
- **`stop`, a refusal, or a request to handle it manually** → stop the run, having changed nothing: `Stopping with the working tree as it is. Commit or set aside what you need, then re-run.`
- **Anything else** — unparseable, a number not in the list, an unclear mix — say which part did not resolve and re-prompt **once**. A second unresolved reply stops the run per the previous case. Two prompts total: the answer is a list of numbers, so a user who cannot give one twice wants to handle it manually.

## Step 3 — Record

**Named paths** → `<precommit_pathspec>`. Do not stage them here; Step 1e.4 commits them once the branch is settled.

**Everything else** → `<keep_dirty_pathspec>` per SKILL.md Step 1e.2's Keep-dirty paths rule. Tell the user one consequence, because it lasts the whole run and is not obvious: these paths are excluded from every phase commit, so if a phase modifies one, that work is left uncommitted in the file alongside their own edits and never reaches the PR.

**If a keep-dirty path is already staged** (porcelain column 1 non-blank and not `?`), `':(exclude)'` cannot evict it from the index, so run `git restore --staged -- <path>` (both paths of a rename) and say so: `Unstaged <path> so it stays out of phase commits — its contents are unchanged.` This never alters file content. If the path was only partially staged, add: `a partial staging selection was reset.`

**Write the record durably.** Update `<scratch_dir>/tree-state.md` now: one `keep-dirty: <path>` line per keep-dirty path, one `input: <path>` line per named input — replace existing lines rather than duplicating, paths unquoted, a rename contributing two lines (one per path). SKILL.md Step 1e.2 reloads this file on every later run, and every staging site consults it when `<keep_dirty_pathspec>` is absent from working memory — the in-context pathspecs are caches of this file, never the other way around.

## Checkout with declared dirt (SKILL.md Step 1e.3)

Named and unnamed paths are both still dirty when Step 1e.3 runs — by design, since Step 1e.4 has not happened yet. Any `git checkout` there can abort with `… would be overwritten by checkout`, including `checkout -b` when HEAD differs from `<base_branch>`. Surface the error verbatim and stop, saying that no commit was made and no file content has changed (any unstaging Step 3 performed was index-only). Never force (`-f`), never stash past it, never re-point the branch to make it succeed.

## Step 1e.4 — Commit the declared inputs

Runs after SKILL.md Step 1e.3 has settled the branch, so these files land on whatever branch the run commits to — the work branch normally, or the current branch under `--no-branch`. Skip entirely when `<precommit_pathspec>` is unset.

1. If anything is already staged beyond the allowlist (`git diff --cached --name-status` shows entries outside `<precommit_pathspec>` — typically an interrupted phase's kept staging; a rename line carries both its paths, which `--name-only` would hide), unstage exactly those entries first — `git restore --staged -- <each>` (both paths of a rename; contents untouched) — and say so: item 3's commit skill commits the whole index, so anything left staged here would be swept into the inputs commit. Then `git add -- <precommit_pathspec>` (unquoted per Step 1) — a literal allowlist. Step 1's `-uall` guarantees these are file paths, not collapsed directories, so this cannot widen. A non-zero exit means a path did not resolve: surface it and stop rather than committing a partial set.
2. `git diff --cached --quiet -- <precommit_pathspec>` — **scoped to the allowlist**. If it reports nothing staged, confirm why before continuing: when those paths are absent from `git status` they were already committed by a prior run, so clear `<precommit_pathspec>`, delete their `input:` lines from `tree-state.md`, and continue (SKILL.md Step 2's reporting item names the prior run's commit); if they are still dirty, item 1 silently failed — stop and surface it, because continuing leaves them for Phase 1's `git add -A` to swallow.
3. `Skill(skill="commit", args="#<plan_sub_issue_number>")` (omit `args` entirely in local-only mode). A sanctioned inline diff read, like Step 4.7's fallback.
4. **Capture `<inputs_commit_sha>`** (`git rev-parse HEAD`) and record it in `tree-state.md` as `inputs-commit: <sha>`, replacing the now-committed `input:` lines and any existing `inputs-commit:` line. Step 5c.5 needs it to scope the branch review past this commit; by then it is many commits back, so the file is what a resume reloads it from. Skip this when item 2 cleared the pathspec — there is no new commit to record.
5. A commit hook rejecting it → `git restore --staged -- <precommit_pathspec>` (leaving the files dirty, contents untouched), then surface the hook output verbatim and stop. Never spawn a Debug agent: this is the user's own prose, not phase work, and an agent silently editing it is the failure mode this step exists to prevent.

Report via SKILL.md Step 2's reporting item — this lands ahead of Step 2's confirmation gate, so the user must be told regardless of whether a branch was created.
