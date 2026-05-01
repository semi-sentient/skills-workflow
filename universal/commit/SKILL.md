---
name: commit
description: Generate a commit message from staged changes and commit. Accepts an optional ticket identifier argument.
---

1. Run `git diff --cached` to see all staged changes. **If the diff is empty**, inform the user that there are no staged changes and suggest they stage files with `git add` before running this command. Do not proceed further.
2. Detect any commit-message rules the repo enforces, so the message conforms on the first attempt and avoids commit-msg hook churn. Check, in order:
   1. `commitlint.config.{js,cjs,mjs,ts}`, `.commitlintrc*`, or a `commitlint` key in `package.json` — if present, read it and honor its rules (allowed `type-enum`, `subject-case`, `header-max-length`, scope rules, etc.).
   2. `.husky/commit-msg` or `.git/hooks/commit-msg` — if it invokes commitlint or another linter, treat that as confirmation the config above is enforced.
   3. `CONTRIBUTING.md`, `.gitmessage`, or a `commit` section in repo docs for stated conventions.
   4. **If none are found**, default to Conventional Commits with a **Sentence-case** subject (first word capitalized, rest lowercase except proper nouns).
3. Analyze the diff to understand what changed.
4. Write a commit message that follows the rules detected in step 2 (or the default), and matches the project's existing style. Commit messages serve as a persistent record for future agents and developers understanding project history — include enough detail that someone reading `git log` can understand _what_ changed and _why_ without reading the diff.
   1. Format with ticket: `type(TICKET-ID): Sentence-case description`
   2. Format without ticket: `type: Sentence-case description`
   3. If step 2 detected a different `subject-case` (e.g. `lower-case`, `start-case`), use that instead.
   4. After the subject line, add a short paragraph explaining the broader context or motivation when it isn't obvious from the subject alone.
   5. Add bullet points describing each meaningful unit of work (components, features, routes, behavioral changes) — not raw file paths.
   6. **If a ticket was provided**, add a `Ticket:` footer at the end of the message body.

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

5. Only ever include details about what's changing in files that are staged for commit.
