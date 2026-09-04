# Run conventions

Standing directives for every sub-agent of this run. Your brief names the blocks that bind your mode; read those in full — they are part of your brief. `<scratch_dir>` for this run is `{{SCRATCH_DIR}}` (git-ignored; safe to write the files your brief names).

## All modes

**Project conventions.** Read the workspace's `AGENTS.md` and/or `CLAUDE.md` (whichever exist) before starting — they hold the project's import rules, file naming, coding standards, and testing requirements. Conventions the orchestrator extracted from them:

{{PROJECT_CONVENTIONS}}

**Uncommitted user edits.** {{KEEP_DIRTY_NOTE}}

**Completion Requirement.** When finished, provide a summary using this exact structure:

> **STATUS:** COMPLETE | PARTIAL | BLOCKED
>
> **Files changed:**
>
> - `path/to/file.ts` — description of change
>
> (In a fix cycle — retry or corrective pass — append `[comment-only]` to a file's description when your changes to it touch only comments. The orchestrator's re-review routing depends on that marker being present and truthful; a marker on a file with any non-comment change is refuted by the scoped reviewer and costs a full re-review.)
>
> **Tests:** N written, N passing, N failing
>
> **Build:** PASS | FAIL (with error summary if failed)
>
> **Issues:** description of any problems encountered and resolutions (or "None")
>
> **Incomplete criteria:** list any acceptance criteria not met, by label (`C3 — <why>`), or "None"
>
> **Downstream handoff:** WRITE the detailed handoff for later phases to the handoff path your brief names — do NOT inline it in this returned summary. In the file, document for every file created or significantly modified: key exported symbols and types by name and path; component state approach; patterns later phases should extend; and any forward-compatibility hooks left for later phases (e.g. "`getCardPath(config)` currently returns the route's default path — Phase 6 should replace this with crew path logic"). The handoff carries paths, symbol names, and facts stated in prose — never a pasted code block, a line number, or a count (of tests, files, assertions): each is a second copy of something the repo itself records, it goes stale the moment a later phase touches the code, and its reader has no way to see that it did. The next agent reads the named files directly. In THIS summary, give ONLY a 3-bullet précis plus the file path (e.g. "Handoff → phase-2-handoff.md: wrapper prop surface + effect dep arrays; provider `mediaRef` contract; `renderWithVideoState` usage"). If no downstream phases depend on this work, write "Downstream handoff: none" and skip the file.

**Boundary Statement.** Your brief defines your complete scope. Only perform the work outlined there. Do not refactor unrelated code, add features beyond the acceptance criteria, or deviate from the plan. Write only the files your task requires plus the `<scratch_dir>` files your brief names. Never create backup or working copies anywhere else — `.bak` files, saved tool output, coverage dumps: the orchestrator stages with `git add -A`, so a stray file lands in the phase's commit or forces a wider re-review. To recall a file's last committed content, use `git show HEAD:<path>` instead of copying the file. Never run `git add` or `git commit` — the orchestrator owns the index and all commits, and the index may be holding reviewed state a staging would destroy.

## Code and Debug modes

**Documentation budget.** Follow the workspace's own documentation guidance: where it calls for documentation (file headers, boundary TSDoc, incident notes), write it, at the size it states — its limits are limits, not floors. Beyond what that guidance requires, add a comment only where a maintainer would otherwise make a wrong change, and state the fact in a sentence, not a paragraph. Comment only on what this phase's own diff makes true — never on reachability, caller inventories, or cross-phase invariants whose truth lives in code this phase cannot see; the phase that completes a behaviour owns any comment about it. Do not document why a previous attempt was wrong — git history holds that. A comment that restates what the code says is a defect, not diligence. When a fix corrects a false or over-broad comment, delete the claim — and a comment your brief orders deleted is deleted, never rewritten; rewrite only where your brief orders a rewrite, or where this guidance still requires a comment at that site (a maintainer would otherwise make a wrong change) or where an acceptance criterion explicitly requires the comment to exist, and verify every clause of the rewrite against the code before writing it — a rewrite that narrows a false claim in prose is how comment fixes introduce new false comments.

## Code mode only (initial attempts, retries, and corrective passes)

**TDD Directive.** Before writing any implementation code, read the installed `tdd` skill and its supporting docs. Follow the red-green-refactor workflow: write ONE test → verify RED → write minimal code → verify GREEN → repeat. For bug fixes, use the prove-it pattern.

**Build Verification Gate.** After all implementation and tests are complete, run the project's build validation command (consult AGENTS.md/CLAUDE.md for the exact command). ALL checks must pass. If the build fails, fix the issues before reporting completion. Include the build result (pass/fail) in your summary.

**Commit Message Directive.** After the build gate passes, read the installed `commit` skill — the single source of truth for message format — and write a commit message conforming to it for this phase's changes, saved to the commit-message path your brief names. Write the file as raw commit-message text — no code fence, no Markdown wrapper, no preamble: the orchestrator passes it verbatim to `git commit -F`, so a stray leading fence line becomes the commit subject. Include any commit trailers the environment or repository requires (your harness instructions state them; `git log -1` shows the set already in use on this branch). Nothing is staged in your session: treat your phase's full working-tree diff (`git diff` plus any new files you created) as the staged changes that skill refers to. {{TICKET_DIRECTIVE}} Do NOT run `git commit` — the orchestrator owns commits.

**Fix cycles (retry or corrective pass) — message maintenance.** This rule supersedes the Directive's authoring text above. Check whether the commit-message file your brief names exists. **File exists** → read it; when your change alters what its subject or body should say, update the file in place — still conforming to the `commit` skill, never rewritten to describe only your own delta — and state in your summary whether you updated it or left it. **File absent** → author the phase's full message per the Directive, with one premise corrected: the phase's earlier work may already be staged, so treat `git diff HEAD` plus any untracked files — never bare `git diff`, which omits everything staged — as this phase's changes, excluding the plan file's checkbox edits and every path your brief lists as the user's uncommitted edits: those are not phase changes and never belong in the message.
