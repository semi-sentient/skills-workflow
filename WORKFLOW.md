# Agent Skills Workflow: From Idea to Implementation

> For a deeper dive into the design and rationale behind each skill, see [WORKFLOW_SKILLS.md](WORKFLOW_SKILLS.md).

This walkthrough shows how four skills chain together to take a rough idea through rigorous design, planning, and automated implementation. A fifth skill, `tdd`, is never invoked directly in this workflow but is leveraged behind the scenes — `write-a-prd` reads it to shape the PRD's Testing Decisions section, and `run-plan` includes a TDD directive in every Code agent brief so that implementation follows a red-green-refactor loop.

The full workflow looks like this:

```
 Conversation 1                              Conversation 2
┌────────────────────────────────────────┐   ┌────────────────────────┐
│ grill-me → write-a-prd → prd-to-plan  ─┼──▶│ run-plan               │
│ (shared context builds throughout)     │   │ (fresh context window) │
└────────────────────────────────────────┘   └────────────────────────┘
                                    plan file
```

Steps 1-3 happen in a **single conversation** so that every decision, clarification, and codebase insight carries forward naturally. Step 4 starts a **new conversation** with a fresh context window — by this point, the plan file contains everything the agent needs, and starting fresh avoids context rot from the long design session.

## Step 1: Stress-test the idea with `grill-me`

Start with your rough idea — it doesn't need to be polished. The `grill-me` skill will interview you relentlessly about every aspect, walking down each branch of the decision tree and resolving dependencies between decisions one by one.

This step forces you to confront the hard questions early: edge cases, scope boundaries, technical constraints, and user experience tradeoffs. The agent provides its own recommended answer for each question, so you're not starting from a blank page.

**Invoke with:** `/grill-me`

**What to expect:**

- A rapid-fire series of questions, asked one at a time
- Questions that the agent can answer by exploring the codebase are answered automatically
- The conversation continues until you've reached a shared understanding of the full design

**Tips:**

- Don't over-prepare. The whole point is to let the questioning surface what you haven't thought about yet.
- Push back on the agent's recommendations when they don't feel right — this is a conversation, not a quiz.
- You'll know this step is done when new questions stop surfacing surprises.

## Step 2: Capture the design as a PRD with `write-a-prd`

With all decisions resolved, immediately invoke `write-a-prd` in the same conversation. The agent already has full context from the grilling session, so it can draft the PRD without re-interviewing you from scratch.

The skill will explore the codebase to verify assumptions, identify deep modules (small interface, large implementation) that can be tested in isolation, and structure everything into a formal PRD saved to the project's plans directory (`.agents/plans/`, `.claude/plans/`, or `.plans/` depending on which agent directories exist).

**Invoke with:** `/write-a-prd`

**What to expect:**

- The agent may ask a few follow-up questions to fill gaps, but far fewer than a cold start
- It will propose module boundaries and check them with you
- The output is a Markdown PRD file at `<plans-dir>/<feature-name>-prd.md` covering: problem statement, solution, user stories, implementation decisions, testing decisions, and scope boundaries

**Tips:**

- Review the user stories carefully — they become the source of truth for what gets built.
- Pay attention to the Testing Decisions section. It defines which modules get tested and what "good tests" look like for this feature.
- Don't skip the module design discussion. This is where you catch architectural mistakes before they're expensive.

## Step 3: Break the PRD into a plan with `prd-to-plan`

Still in the same conversation, invoke `prd-to-plan` to break the PRD into a phased implementation plan. Each phase is a thin vertical slice (tracer bullet) that cuts through all integration layers end-to-end — not a horizontal slice of one layer.

This step is iterative. The agent will present the proposed phases, ask for your feedback on granularity, and refine until you approve. It then verifies every phase against the actual codebase (checking file paths, function signatures, and cross-phase coherence) and scores each phase for implementation confidence.

**Invoke with:** `/prd-to-plan`

**What to expect:**

- A proposed breakdown of phases, each with a title and the user stories it covers
- An interactive review loop where you can request merges, splits, or reordering
- A verification pass with confidence scores (0-10) for each phase
- The final plan saved to `<plans-dir>/<feature-name>-plan.md` with checkboxed acceptance criteria per phase

**Tips:**

- Push for thinner slices. If a phase touches more than a few files across multiple layers, it can probably be split.
- Watch the confidence scores. Anything below 9 means the agent isn't sure an implementing agent can execute the phase from the plan alone — add more detail until it gets there.
- The plan file is the handoff artifact. Once you're happy with it, everything needed for implementation is in this file.

## Step 4: Run the plan with `run-plan`

Start a **new conversation** for this step. The plan file from Step 3 contains all architectural decisions, phase descriptions, and acceptance criteria — the executing agent doesn't need the design history.

Starting fresh is intentional: after a long design conversation, the context window is full of exploratory back-and-forth that would dilute the agent's focus. A clean context window means the orchestrator and its sub-agents operate with maximum clarity.

The `run-plan` skill reads the plan, presents an execution summary for your confirmation, then works through each phase sequentially — spawning specialized sub-agents (Research, Code, Architect, Debug) as needed. It checks off acceptance criteria in the plan file as phases complete, so progress is persistent and resumable.

**Invoke with:** `/run-plan <plans-dir>/<feature-name>-plan.md`

**What to expect:**

- An execution summary showing all phases and which agent mode each will use
- Research agents gathering codebase context before implementation begins
- Sequential phase execution with progress tracking after each phase
- Automatic error handling: failed phases trigger Debug agents or context-enriched retries
- A final summary of what was accomplished, any caveats, and remaining follow-ups

**Tips:**

- Review the execution summary before confirming. This is your last chance to catch phase ordering issues or missing context.
- If a conversation is interrupted mid-execution, you can re-run `/run-plan` on the same plan file — it reads the checkboxes to determine which phases are already complete and picks up where it left off.
- The orchestrator stays lean (it doesn't read source code or run tests itself), so your context window is reserved for coordination, not implementation details.

## Why two conversations?

The conversation boundary between Steps 3 and 4 is a deliberate design choice:

- **Steps 1-3** benefit from shared context. Each skill builds on the decisions and codebase understanding from the previous step. Re-establishing this context in a new conversation would be wasteful and lossy.
- **Step 4** benefits from a fresh start. The plan file is a self-contained artifact. The design exploration, dead ends, and back-and-forth from the first conversation would only add noise. A clean context window lets the orchestrator and its sub-agents focus entirely on execution.

Think of the plan file as the contract between the two conversations. Steps 1-3 produce it; Step 4 consumes it.

## Where to start

Not everyone needs to run the full pipeline every time. Where you start depends on what you already have:

- **You have a rough idea.** Start at Step 1 (`grill-me`). The interview will sharpen your thinking before anything gets written down.
- **You have a clear design but no formal requirements.** Skip the grilling and start at Step 2 (`write-a-prd`). You already know what you want — you just need it captured in a structured format.
- **You already have a PRD.** Start at Step 3 (`prd-to-plan`). Point the skill at your existing PRD and it will break it into phased execution.
- **You already have a plan.** Start at Step 4 (`run-plan`). If someone else wrote the plan — or you wrote it by hand — you can execute it directly.

The earlier you start, the more ambiguity gets resolved before code is written. But if a prior step has already been handled through other means (a design doc, a team discussion, a spec from product), there's no need to repeat it.
