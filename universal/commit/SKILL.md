---
name: commit
description: Generate a commit message from staged changes, preview, and commit. Accepts an optional ticket identifier argument.
---

1. Run `git diff --cached` to see all staged changes. **If the diff is empty**, inform the user that there are no staged changes and suggest they stage files with `git add` before running this command. Do not proceed further.
2. Analyze the diff to understand what changed.
3. Write a commit message that follows the Conventional Commits specification and matches the project's existing style, based on the diff and optional ticket identifier passed. Commit messages serve as a persistent record for future agents and developers understanding project history — include enough detail that someone reading `git log` can understand _what_ changed and _why_ without reading the diff.
    1. Format with ticket: `type(TICKET-ID): description`
    2. Format without ticket: `type: description`
    3. After the subject line, add a short paragraph explaining the broader context or motivation when it isn't obvious from the subject alone.
    4. Add bullet points describing each meaningful unit of work (components, features, routes, behavioral changes) — not raw file paths.
    5. **If a ticket was provided**, add a `Ticket:` footer at the end of the message body.

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

4. Only ever include details about what's changing in files that are staged for commit.
5. ALWAYS show the generated message and ask for confirmation before running the `git commit` command.
