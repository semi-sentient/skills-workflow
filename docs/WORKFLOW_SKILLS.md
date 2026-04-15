# Agent Skills Workflow: Skills in Depth

> For a step-by-step walkthrough of the full workflow, see [WORKFLOW.md](WORKFLOW.md).

## Grill Me

### What it does

A structured interview that pressure-tests your design before any code is written — rigorous, but collaborative.

### Key points

1. **You don't need all the answers upfront — that's the point.** The skill is designed for you to think out loud and refine your thinking in real time. It asks hard questions, but it's a thinking partner, not an interrogator.
2. **Cheapest place to find problems is before you write code.** A design flaw caught during planning costs minutes to fix. The same flaw caught after implementation costs hours or days. Grill-me forces you to confront gaps early.
3. **It resolves the decision tree.** Most features have branching decisions — edge cases, tradeoffs, scope boundaries. This skill systematically walks each branch until you've made an explicit choice, rather than leaving ambiguity for the coding agent to guess at.
4. **It simulates the questions your team would ask in a design review** — but you get them before you've invested effort. "What happens when X?" "Have you considered Y?" "Why not Z?" These are the questions that derail PRs if left unanswered.
5. **It builds shared context between you and the agent.** By the end of the interview, the agent deeply understands your intent, constraints, and priorities. Everything downstream — the PRD, the plan, the code — benefits from that shared understanding.

---

## Write a PRD

### What it does

Produces a structured product requirements document through guided interview and codebase exploration.

### Key points

1. **It bridges the gap between "I have an idea" and "here's what we're building."** A lot of engineering time is wasted building the wrong thing because requirements were never written down clearly. This skill forces that clarity.
2. **It explores the codebase while interviewing you.** The PRD isn't written in a vacuum — the agent reads existing code, understands current patterns, and grounds the requirements in the reality of what already exists. The output is feasible by design.
3. **It captures the "why" alongside the "what."** Good PRDs don't just list features — they document motivation, success criteria, and scope boundaries. This gives future-you (or anyone reading the PRD) the context to make good judgment calls during implementation.
4. **TDD is baked in from the start.** The PRD doesn't just describe features — it describes testable behaviors. By defining what "correct" looks like at the requirements level, you set up every downstream phase for test-driven development. Tests aren't an afterthought bolted on during implementation; they're a first-class output of the requirements process. This means by the time the coding agent picks up a phase, it already knows what test to write first.
5. **User stories double as your verification checklist.** The user stories in the PRD map directly to what you need to verify when the feature is done — "As a user, I can X" becomes "open the app and confirm you can X." You don't have to reverse-engineer what the feature is supposed to do from the code. And as we build confidence in this workflow, those same stories become the basis for automated end-to-end tests, moving us toward a future where QA is fully automated.
6. **It drives toward deep module design.** The PRD encourages you to think about interfaces early — what does the consumer of this feature actually need to know? The goal is that the feature's API stays simple even as the implementation grows complex. The result is code that's more testable, more maintainable, and more navigable — for both humans and AI agents.
   - *For the engineers:* This is the "deep module" concept from John Ousterhout's *A Philosophy of Software Design* — small, simple interfaces hiding rich implementation. A large interface with thin implementation just passes complexity to the caller. By thinking about this at the requirements level, you avoid the shallow module trap where every internal detail leaks into the API.
7. **It's the input to everything that follows.** The PRD feeds directly into the planning skill. Without a clear PRD, plans are vague and agents make assumptions. Garbage in, garbage out — this skill prevents the garbage-in.

---

## PRD to Plan

### What it does

Transforms a PRD into a phased implementation plan using tracer-bullet vertical slices.

### Key points

1. **You build a working skeleton before adding muscle.** Instead of building all the backend, then all the frontend, then wiring them together and praying — you build a thin slice through every layer first. You prove the architecture works before you invest in breadth.
   - *For the engineers:* This is the "tracer bullet" approach from *The Pragmatic Programmer* — fire one round through the full stack to see if you hit the target, then adjust aim before committing to the full volley.
2. **Each phase is a self-contained deliverable.** You can stop after any phase and have something that works. This is critical for managing scope, getting early feedback, and avoiding the "90% done, 90% left" trap.
3. **It encodes all the decisions from the grill-me and PRD into actionable steps.** The coding agent doesn't need to re-derive your intent. Every step has enough context — what to build, where to build it, why it's built that way, and what constraints to respect.
4. **The plan tracks how code evolves across phases.** When something introduced in an early phase gets modified later, the plan says so — clearly. Both phases reference the change so nothing is silently overwritten or rebuilt from scratch.
   - *Technical detail:* The earlier phase notes that it will be extended later. The later phase describes the exact before-and-after change. This prevents implementing agents from getting confused about the current state of shared code across phase boundaries.
5. **Future needs are designed in, not patched on.** The plan identifies where to leave deliberate seams for later phases — not speculative abstractions, but specific hooks based on known future work defined in the plan itself.
   - *Technical detail:* This takes two forms: extension points that later phases will populate (like a response DTO with an empty metadata map that Phase 4 fills in), and abstraction points that later phases will override (like a path resolver function that Phase 6 swaps for tenant-specific routing).
6. **Plan verification catches errors before a single line of code is written.** Before the plan is finalized, every referenced source file is re-read against the actual codebase — not from memory, not from a stale summary. File paths, function signatures, component hierarchies, interfaces — all verified. Cross-phase coherence is checked to ensure later modifications won't silently break earlier tests. Every ambiguous phrase like "either/or" is resolved to a single prescriptive decision. Each phase gets a confidence score from 0 to 10 for how likely a coding agent will implement it correctly from the plan alone — anything below a 9 gets revised. This catches the number one source of plan errors: working from stale assumptions instead of real files.
7. **It separates planning from execution.** When you plan and code simultaneously, you make expedient choices that create tech debt. By planning first, you can see the full shape of the work and make architectural decisions with full information.

---

## Run Plan

### What it does

Executes a multi-phase implementation plan by orchestrating specialized sub-agents, each with a fresh context window and a tightly scoped brief.

### Key points

1. **It exists to solve context rot.** A complex implementation plan can have a dozen phases and take hours to complete. If you execute that in a single conversation, you inevitably hit the "dumb zone" — the model's output quality degrades as the context window fills with stale code diffs, old test output, and resolved debugging tangents. By delegating each phase to a sub-agent with a fresh context window and a tightly scoped brief, the orchestrator keeps every agent working in the sharp zone. With a properly structured plan, each sub-agent rarely exceeds 10% of its 1M-token context window — even for large, multi-phase features. The orchestrator holds more context but typically stays below 20%.
2. **It's a strategic orchestrator, not a code writer.** The run-plan agent never reads source code, never runs tests, never implements anything itself. Its entire job is coordination — composing briefs, spawning the right agent for the job, tracking progress, and carrying knowledge forward between phases. This separation of concerns is what makes it scale.
3. **Each phase gets a purpose-built agent.** The orchestrator selects from specialized agent modes — Research agents to gather codebase context, Code agents for TDD implementation, Architect agents to resolve design ambiguities, and Debug agents to diagnose failures. Each agent gets a fresh context window, which means it's not polluted by the details of earlier phases. It only sees what it needs.
4. **Context transfer is structured, not accidental.** When a Code agent finishes a phase, it reports back a structured summary — exported interfaces, function signatures, patterns established, forward-compatibility hooks. The orchestrator carries that context forward into the next phase's brief. This is how Phase 3 knows what Phase 2 actually built, even though it's a completely different agent with no shared memory.
5. **Research happens before implementation.** Before any code is written, the orchestrator spawns Research agents in parallel to scan referenced files, APIs, patterns, and cross-phase dependencies. This front-loads the context gathering so that Code agents can focus on building, not hunting.
6. **Every agent brief follows a strict 8-section structure.** Role, codebase context, file manifest, scoped task, TDD directive, build verification gate, completion requirements, and boundary statement. This isn't bureaucracy — it's precision. The brief is the contract. A vague brief produces vague code. A precise brief produces code that matches the plan.
7. **TDD is enforced at the agent level.** Every Code agent brief includes an explicit TDD directive — red-green-refactor before implementation. And a build verification gate — all checks must pass before the agent can report completion. The agent doesn't get to decide whether to write tests. That decision was already made in the PRD.
8. **It's resumable.** The plan file is the persistent record. Acceptance criteria checkboxes get checked off as phases complete. If the process is interrupted — context limit, error, user pause — you re-run the skill on the same plan file. Completed phases are skipped, partially-completed phases are re-attempted. No work is lost.
9. **Failures are diagnosed, not retried blindly.** When a phase fails, the orchestrator doesn't just re-run it with the same instructions. It spawns a Debug or Research agent to understand what went wrong, adjusts the brief, and retries with new information. After two retries, it escalates to the user rather than spinning.

---

## Overarching Narrative

These skills form a pipeline — `grill-me` sharpens the thinking, `write-a-prd` captures it as requirements with testability and deep module design baked in, `prd-to-plan` turns it into verified, phased execution with explicit cross-phase contracts, and `run-plan` orchestrates the implementation through specialized agents with structured context transfer. Each step reduces ambiguity so that by the time code is written, the agent is executing a well-understood plan rather than guessing at your intent.
