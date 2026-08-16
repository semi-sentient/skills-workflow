---
name: commit
description: Generate a commit message from staged changes and commit. Accepts an optional ticket identifier argument; when omitted, infers an issue reference from the branch name or conversation (`--no-ticket` suppresses inference).
---

1. Run `git diff --cached` to see all staged changes. **If the diff is empty**, inform the user that there are no staged changes and suggest they stage files with `git add` before running this command. Do not proceed further.
2. Resolve the ticket identifier:
   1. If a ticket argument was supplied, use it — it always wins; skip the rest of this step. The argument `--no-ticket` (or the invoker explicitly asking for no ticket) also skips the rest of this step: write the message without one — inference never overrides a deliberate omission.
   2. Otherwise, check the current branch name (`git branch --show-current`) for an issue reference. Only these patterns count:
      - `#<digits>` anywhere in the name
      - `issue-<digits>` or `issues/<digits>`
      - `<digits>-<slug>` at the start of a path segment (`123-fix-login`, `feat/123-fix-login`)
      - an uppercase project key with a number (`SALES-456`)
      - a lowercase tracker key with a number at the start of a path segment that follows another segment (Linear's `markus/eng-142-fix-login`, Shortcut's `markus/sc-1234/fix-login`); uppercase the key on output (`ENG-142`). In a first or only segment, a lowercase word before digits is a type or word prefix, not a key — `fix-123-login` yields nothing

      These exclusions override every pattern above. Digits embedded in an ordinary word, version, or date are not references — `chore/bump-node-22`, `v2-api`, `2026-08-15-hotfix`, `dependabot/npm_and_yarn/lodash-4.17.21`, and `renovate/node-22.x` yield nothing (a package name is not a tracker key). Well-known standards identifiers are not project keys — `fix/CVE-2024-21538`, `RFC-7231`, `SHA-256`, `ISO-8601` yield nothing.
   3. Otherwise, use the issue the conversation explicitly ties to the staged work (e.g. the user asked for this change by issue number or link). A passing mention of an issue that isn't the subject of the staged changes does not count.
   4. If nothing resolves, proceed without a ticket exactly as before. If the repo's recent history shows a ticket convention (several recent subjects in `git log --oneline -15` carry an issue reference — a `type(#123):` or `type(KEY-123):` scope, a `KEY-123:` prefix, or a trailing `(#123)`), note in one line — in your reply, never inside the commit message — that no issue reference was found so the user can decide; otherwise say nothing. Never prompt, gate, or retry over a missing reference.

   Format a bare issue number as `#<digits>`; keep project-key identifiers as-is. An inferred ticket is used exactly like a supplied one in the steps below.
3. Detect any commit-message rules the repo enforces, so the message conforms on the first attempt and avoids commit-msg hook churn. Check, in order:
   1. `commitlint.config.{js,cjs,mjs,ts}`, `.commitlintrc*`, or a `commitlint` key in `package.json` — if present, read it and honor its rules (allowed `type-enum`, `subject-case`, `header-max-length`, scope rules, etc.).
   2. `.husky/commit-msg` or `.git/hooks/commit-msg` — if it invokes commitlint or another linter, treat that as confirmation the config above is enforced.
   3. `CONTRIBUTING.md`, `.gitmessage`, or a `commit` section in repo docs for stated conventions.
   4. **If none are found**, default to Conventional Commits with a **Sentence-case** subject (first word capitalized, rest lowercase except proper nouns).
4. Analyze the diff to understand what changed.
5. Write a commit message that follows the rules detected in step 3 (or the default), and matches the project's existing style. Commit messages serve as a persistent record for future agents and developers understanding project history — include enough detail that someone reading `git log` can understand _what_ changed and _why_ without reading the diff.
   1. Format with ticket: `type(TICKET-ID): Sentence-case description`. If step 3 detected scope rules the ticket would violate (a `scope-enum` that doesn't include it, a `scope-case` it can't satisfy), use the no-ticket header format instead and keep the ticket in the `Ticket:` footer.
   2. Format without ticket: `type: Sentence-case description`
   3. If step 3 detected a different `subject-case` (e.g. `lower-case`, `start-case`), use that instead.
   4. After the subject line, add a short paragraph explaining the broader context or motivation when it isn't obvious from the subject alone.
   5. Add bullet points describing each meaningful unit of work (components, features, routes, behavioral changes) — not raw file paths.
   6. **If a ticket was resolved in step 2** (supplied or inferred), add a `Ticket:` footer as the final line, separated from the body by a blank line (commitlint's `footer-leading-blank` rule warns otherwise).

   Example:

   ```
   feat(SALES-456): Add Sales Performance dashboard

   Add a new dashboard for sales leadership to track revenue,
   pipeline health, and rep performance at a glance.

   - Add RevenueKPICards showing MTD revenue, deals closed,
     average deal size, and quota attainment with period-over-period deltas
   - Add PipelineFunnelChart visualizing deal progression across
     stages from prospecting through closed-won
   - Add RevenueTrendChart with 12-month line chart and
     quarterly target overlay
   - Add RepLeaderboard ranked by closed revenue with sortable
     columns for deals, win rate, and average cycle time
   - Add DateRangeFilter and TeamFilter controls wired to
     shared dashboard state
   - Integrate sales route and nav menu entry

   Ticket: SALES-456
   ```

6. Only ever include details about what's changing in files that are staged for commit.
