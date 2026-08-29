# Agent Skills Workflow: From Idea to Implementation

> For a deeper dive into the design and rationale behind each skill, see [WORKFLOW_SKILLS.md](WORKFLOW_SKILLS.md).

This walkthrough shows how four skills chain together to take a rough idea through rigorous design, planning, and automated implementation. Two supporting skills, `tdd` and `commit`, are never invoked directly in this workflow but are leveraged behind the scenes: `write-a-prd` reads `tdd` to shape the PRD's Testing Decisions section, `run-plan` includes a TDD directive in every Code agent brief, and `run-plan` uses `commit` as the source of truth for each phase's Conventional Commits message — the phase's Code agent authors the message against that skill, and the orchestrator invokes `/commit` directly when that fast path doesn't apply.

The full workflow looks like this:

```
 Conversation 1                                     Conversation 2
┌───────────────────────────────────────────────┐   ┌────────────────────────┐
│ grill-with-docs → write-a-prd → prd-to-plan  ─┼──▶│ run-plan               │
│ (shared context builds throughout)            │   │ (fresh context window) │
└───────────────────────────────────────────────┘   └────────────────────────┘
                                     plan file or GH issue
```

Steps 1-3 happen in a **single conversation** so that every decision, clarification, and codebase insight carries forward naturally. Step 4 starts a **new conversation** with a fresh context window — by this point, the plan (local file or published GitHub sub-issue) contains everything the agent needs, and starting fresh avoids context rot from the long design session.

### When the full flow pays off

The pipeline is worth running end-to-end when there's design ambiguity to resolve and multi-phase implementation ahead. For small bug fixes, one-off refactors, or changes contained to a single file, skip the PRD and plan entirely — work directly with `/tdd` for behavior changes or `/commit` for straightforward edits. The [Where to start](#where-to-start) section covers how to pick up the pipeline mid-way when earlier artifacts already exist.

### GitHub integration at a glance

`write-a-prd`, `prd-to-plan`, and `run-plan` can all optionally use GitHub when the project has a `github.com` remote and `gh` is authenticated:

- `write-a-prd` publishes the PRD as an issue with the `epic` label
- `prd-to-plan` publishes the plan as a sub-issue of that epic
- `run-plan` creates a `plan/<slug>` work branch, commits per phase, syncs progress to the plan sub-issue, and opens a PR linking back to both the sub-issue and the epic

Each skill accepts `--no-github` to stay local-only, and `run-plan` exposes finer-grained flags for teams that manage the git/GH ceremony themselves. See [Flag Recipes](#flag-recipes) for the full reference and common combinations.

## Step 1: Stress-test the idea with `grill-with-docs` (or `grill-me`)

Start with your rough idea — it doesn't need to be polished. The `grill-with-docs` skill will interview you relentlessly about every aspect, walking down each branch of the decision tree and resolving dependencies between decisions one by one — capturing terminology decisions to `CONTEXT.md` and offering ADRs inline as they emerge. Use `grill-me` instead if you don't want those documentation side-effects.

This step forces you to confront the hard questions early: edge cases, scope boundaries, technical constraints, and user experience tradeoffs. The agent provides its own recommended answer for each question, so you're not starting from a blank page.

**Invoke with:** `/grill-with-docs` (or `/grill-me` if you don't want the inline `CONTEXT.md` / ADR maintenance).

**What to expect:**

- Numbered rounds of questions — every question that is answerable right now arrives in one round, each with the agent's recommendation
- Your answers unlock the next round: questions that depended on a decision you just made become askable, and the agent recomputes what to ask
- Questions the agent can answer by exploring the codebase are answered automatically; the agent may also re-explore mid-interview when a new constraint reshapes later branches
- When you answer directly (rather than picking from options the agent offered), expect one counter-challenge before the agent accepts and moves on
- A structured wrap-up at the end: decisions made, assumptions accepted (each with a one-line justification), open questions still requiring resolution — any default you didn't explicitly confirm lands in assumptions or open questions, never silently in decisions

**Tips:**

- Don't over-prepare. The whole point is to let the questioning surface what you haven't thought about yet.
- Push back on the agent's recommendations when they don't feel right — this is a conversation, not a quiz.
- You'll know this step is done when new questions stop surfacing surprises.

## Step 2: Capture the design as a PRD with `write-a-prd`

With all decisions resolved, immediately invoke `write-a-prd` in the same conversation. The agent already has full context from the grilling session, so it can draft the PRD without re-interviewing you from scratch.

The skill will explore the codebase to verify assumptions, identify deep modules (small interface, large implementation) that can be tested in isolation, and structure everything into a formal PRD saved to the project's plans directory (`.agents/plans/`, `.claude/plans/`, or `.plans/` depending on which agent directories exist).

**Invoke with:** `/write-a-prd` (or `/write-a-prd --no-github` to force local-only)

**What to expect:**

- The agent may ask a few follow-up questions to fill gaps, but far fewer than a cold start
- It will propose module boundaries and check them with you
- The output is a Markdown PRD file at `<plans-dir>/<feature-name>-prd.md` covering: problem statement, solution, user stories, implementation decisions, testing decisions, and scope boundaries
- If the project has a GitHub remote and `gh` is authenticated, the skill then prompts to publish the file as a GitHub issue labeled `epic`. Review (and edit) the file first, then reply `publish` or `cancel`. Publishing adds a `GH Issue:` header and a `<!-- gh-issue: N -->` footer to the local file, which is how `prd-to-plan` picks up the linkage automatically.

**Tips:**

- Review the user stories carefully — they become the source of truth for what gets built.
- Pay attention to the Testing Decisions section. It defines which modules get tested and what "good tests" look like for this feature.
- Don't skip the module design discussion. This is where you catch architectural mistakes before they're expensive.
- If you re-invoke `/write-a-prd` for a PRD that already exists, the skill detects it and offers to overwrite, publish the existing file as a new GH issue, or cancel — useful when the first publish failed or you've edited the file after publishing.

## Step 3: Break the PRD into a plan with `prd-to-plan`

Still in the same conversation, invoke `prd-to-plan` to break the PRD into a phased implementation plan. Each phase is a thin vertical slice (tracer bullet) that cuts through all integration layers end-to-end — not a horizontal slice of one layer.

This step is iterative. The agent will present the proposed phases, ask for your feedback on granularity, and refine until you approve. It then verifies every phase against the actual codebase (checking file paths, function signatures, and cross-phase coherence) and scores each phase for implementation confidence.

**Invoke with:** `/prd-to-plan` (or `/prd-to-plan --no-github` to stay local-only, or `/prd-to-plan #123` to explicitly link a plan to an existing PRD-epic issue)

**What to expect:**

- A proposed breakdown of phases, each with a title and the user stories it covers
- An interactive review loop where you can request merges, splits, or reordering
- A verification pass with confidence scores (0-10) for each phase
- The final plan saved to `<plans-dir>/<feature-name>-plan.md` with checkboxed acceptance criteria per phase
- If the PRD was published to GitHub in Step 2, the skill detects the `<!-- gh-issue: N -->` footer and prompts to publish the plan as a sub-issue of that epic (label `plan`). Confirm with `create`, or `cancel` to keep the plan local. On success, the local plan file gets a `<!-- gh-sub-issue: N -->` footer so `run-plan` can pick it up by issue number.

**Tips:**

- Push for thinner slices. If a phase touches more than a few files across multiple layers, it can probably be split.
- Watch the confidence scores. Anything below 9 means the agent isn't sure an implementing agent can execute the phase from the plan alone — add more detail until it gets there.
- The plan file is the handoff artifact. Plans describe _what to build and how to verify it_ — they deliberately exclude the git/GH ceremony (work branch, per-phase commits, PR) because `run-plan` handles that uniformly. This keeps plans clean regardless of which opt-out flags the user picks later.

## Step 4: Run the plan with `run-plan`

Start a **new conversation** for this step. The plan (local file or GitHub sub-issue) contains all architectural decisions, phase descriptions, and acceptance criteria — the executing agent doesn't need the design history.

Starting fresh is intentional: after a long design conversation, the context window is full of exploratory back-and-forth that would dilute the agent's focus. A clean context window means the orchestrator and its sub-agents operate with maximum clarity.

The `run-plan` skill reads the plan, presents an execution summary for your confirmation, then works through each phase sequentially — spawning specialized sub-agents (Research, Code, Architect, Debug, Review) as needed. An independent Review agent audits each Code phase's changes against its acceptance criteria before anything is committed, and criteria are checked off as they're verified — so progress is persistent and resumable.

**Invoke with one of:**

- `/run-plan <plans-dir>/<feature-name>-plan.md` — pass the local plan file path
- `/run-plan #123` — pass the plan sub-issue number (GitHub-backed plans only)
- `/run-plan https://github.com/<org>/<repo>/issues/123` — pass the full issue URL

When given a `#N` or URL, `run-plan` first looks for a local file with a matching `<!-- gh-sub-issue: N -->` footer; if none exists, it fetches the body from GitHub and writes it to `<plans-dir>/<slug>-plan.md`. Either form works — hand someone just an issue number and they have everything they need.

**What to expect:**

- If the working tree is dirty, a numbered prompt asking which uncommitted paths are this work's input — a dirty tree does not block the run. This fires routinely on this walkthrough: step 1's `grill-with-docs` writes `CONTEXT.md` and ADRs without committing them, and they reach `run-plan` as its input. Reply with their numbers and they land as their own commit ahead of Phase 1 rather than folded into it; anything you don't name (a steering doc you're testing, say) stays untouched all run; reply `stop` to end the run and handle a path yourself. No file ever leaves the working tree to resolve a dirty tree — nothing is reverted, deleted, or stashed
- An execution summary showing all phases, which agent mode each will use, the work branch it will create (`plan/<slug>`), and whether GH sync is active
- A `plan/<slug>` work branch created from the repo default (override with `--base <branch>`)
- Research agents gathering codebase context before implementation begins
- Sequential phase execution with progress tracking (per-phase active time and per-mode token cost) after each phase
- An independent review gate after each Code phase — a fresh Review agent audits the staged changes against the phase's acceptance criteria before they're checked off or committed (`--no-review` to skip)
- A per-phase commit referencing the plan sub-issue for narrow-scope traceability — the message is authored against the `commit` skill by the phase's Code agent, with `/commit` invoked directly as the fallback
- Plan progress synced to the linked GitHub sub-issue body after each phase (GH-backed runs)
- Automatic error handling: failed phases trigger Debug agents; failed pre-commit hooks trigger a Debug agent rather than `--no-verify` bypass
- A final summary comment posted to the plan sub-issue, the branch pushed to origin, a pre-PR branch review hunting integration bugs between phases (`--no-branch-review` to skip; a confirmed bug opens the PR as a draft), and a PR opened against the base branch (linking `Closes #<plan-sub-issue>` and `Refs #<prd-epic>`)

**Tips:**

- Review the execution summary before confirming. This is your last chance to catch phase ordering issues or missing context.
- Re-run on the same argument to resume. `run-plan` reads the checked acceptance criteria from the plan (or the synced GitHub body) and skips phases that already appear complete. If the `plan/<slug>` branch exists with unpushed commits, it's reused — not recreated.
- Cross-machine resume works for GitHub-backed plans. Because per-phase sync keeps the sub-issue body in lockstep with the local file, you can start a run on one machine, stop, and pick up on another by passing the same `#N` to `/run-plan` — the skill fetches the latest body and resumes.
- The orchestrator stays lean (it doesn't read source code or run tests itself), so your context window is reserved for coordination, not implementation details.
- To tailor the git/GH ceremony — skip the PR, commit directly to the current branch, etc. — see [Flag Recipes](#flag-recipes).

## Why two conversations?

The conversation boundary between Steps 3 and 4 is a deliberate design choice:

- **Steps 1-3** benefit from shared context. Each skill builds on the decisions and codebase understanding from the previous step. Re-establishing this context in a new conversation would be wasteful and lossy.
- **Step 4** benefits from a fresh start. The plan file is a self-contained artifact. The design exploration, dead ends, and back-and-forth from the first conversation would only add noise. A clean context window lets the orchestrator and its sub-agents focus entirely on execution.

Think of the plan file as the contract between the two conversations. Steps 1-3 produce it; Step 4 consumes it.

## Where to start

Not everyone needs to run the full pipeline every time. Where you start depends on what you already have:

- **You have a rough idea.** Start at Step 1 (`grill-with-docs` or `grill-me`). The interview will sharpen your thinking before anything gets written down.
- **You have a clear design but no formal requirements.** Skip the grilling and start at Step 2 (`write-a-prd`). You already know what you want — you just need it captured in a structured format.
- **You already have a PRD.** Start at Step 3 (`prd-to-plan`). Point the skill at your existing PRD and it will break it into phased execution.
- **You already have a plan.** Start at Step 4 (`run-plan`). If someone else wrote the plan — or you wrote it by hand — you can execute it directly.

The earlier you start, the more ambiguity gets resolved before code is written. But if a prior step has already been handled through other means (a design doc, a team discussion, a spec from product), there's no need to repeat it.

## Flag Recipes

The default flow assumes GitHub is configured and produces per-phase commits on a `plan/<slug>` work branch, culminating in a PR. Flags let you opt out of individual pieces of that ceremony without rewriting the plan. The commands below are slash commands invoked inside your coding agent (Claude Code, Cursor, Roo, etc.) — they are not shell commands.

### Flag reference

| Skill          | Flag              | Purpose                                                                              |
| -------------- | ----------------- | ------------------------------------------------------------------------------------ |
| `/write-a-prd` | `--no-github`     | Skip the publish prompt — keep the PRD as a local file only                          |
| `/prd-to-plan` | `--no-github`     | Skip the sub-issue prompt — keep the plan as a local file only                       |
| `/run-plan`    | `--no-github`     | Force local-only mode (no progress sync, no PR) even when GH metadata is present     |
| `/run-plan`    | `--no-branch`     | Skip creating a work branch; use the current branch for all commits                  |
| `/run-plan`    | `--no-pr`         | Skip opening the PR at end of run                                                    |
| `/run-plan`    | `--allow-main`    | Permit committing to the default branch when `--no-branch` is set                    |
| `/run-plan`    | `--base <branch>` | Override the base branch for the work branch and PR (defaults to repo default)       |
| `/run-plan`    | `--draft`         | Open the PR as a draft regardless of run outcome                                     |
| `/run-plan`    | `--no-review`     | Skip the per-phase review gate that audits each Code phase's changes before commit   |
| `/run-plan`    | `--no-branch-review` | Skip the pre-PR review of the full branch diff                                    |

`--no-github` on `/write-a-prd` and `/prd-to-plan` means the artifact is never published. `--no-github` on `/run-plan` means progress is not synced and no PR is opened — but a local file with a `<!-- gh-sub-issue: N -->` footer is still valid input; the flag just suppresses the GH side of the run.

### Common combinations

**Default — full GitHub workflow:**

```
/write-a-prd
/prd-to-plan
# (new conversation)
/run-plan #123
```

PRD becomes a GH epic, plan becomes a sub-issue, `/run-plan` creates a work branch, commits per phase, syncs progress to the sub-issue, and opens a PR at the end.

**Local-only — no GitHub at any stage:**

```
/write-a-prd --no-github
/prd-to-plan --no-github
# (new conversation)
/run-plan .agents/plans/<slug>-plan.md
```

PRD and plan stay as local files. `/run-plan` detects local mode automatically from the plan file (no `<!-- gh-sub-issue -->` footer) and skips the PR step. A work branch is still created and phases are still committed — this recipe only opts out of GitHub, not the git ceremony.

**Execute directly on main — no work branch:**

```
/run-plan .agents/plans/<slug>-plan.md --no-branch --allow-main
```

`--no-branch` keeps the current branch; `--allow-main` overrides the built-in refusal to commit to the default branch without explicit opt-in. Per-phase commits land directly on main. The push and PR steps are skipped automatically.

**Resume an interrupted run:**

```
/run-plan #123
```

Re-invoke with the same argument. `/run-plan` reads checked acceptance criteria from the plan (or the synced GitHub sub-issue) and skips phases that already appear complete. If the `plan/<slug>` branch exists with unpushed commits, it's reused rather than recreated.
