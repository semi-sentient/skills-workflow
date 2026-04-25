# skills-workflow

Agent skills workflow with an emphasis on orchestration during execution that works across Claude Code, Cursor, Roo, and other agent harnesses.

## Recommended Workflow

These skills are designed to chain together. See [WORKFLOW.md](docs/WORKFLOW.md) for a guided walkthrough of the full idea-to-implementation workflow using `grill-me` → `write-a-prd` → `prd-to-plan` → `run-plan`.

## Installation

Requires [Node.js](https://nodejs.org/). Install these skills into any project using the [Vercel Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills@latest add semi-sentient/skills-workflow \
  --skill commit \
  --skill grill-me \
  --skill prd-to-plan \
  --skill run-plan \
  --skill tdd \
  --skill write-a-prd \
  -y
```

By default, skills are installed to all detected agent directories in the project. Use `--agent` to target a specific agent:

```bash
# Claude Code only (.claude/skills/)
npx skills@latest add semi-sentient/skills-workflow --agent claude-code --skill <skill-name>

# Agent-agnostic (.agents/skills/)
npx skills@latest add semi-sentient/skills-workflow --agent agents --skill <skill-name>
```

## Updating

Update all installed skills to the latest version:

```bash
npx skills@latest update
```

Update a specific skill:

```bash
npx skills@latest update <skill-name>
```

> **Claude Code users:** The `update` command does not support `--agent` and may create an `.agents/skills/` directory even in projects that only use `.claude/`. To update without this side effect, re-run `add` with `--agent claude-code`:
>
> ```bash
> npx skills@latest add semi-sentient/skills-workflow --agent claude-code --skill <skill-name> -y
> ```

## Available Skills

### Universal

Skills that apply to all projects regardless of language or framework.

| Skill | Description |
| --- | --- |
| `grill-me` | Stress-test a plan or design through relentless questioning, resolving each branch of the decision tree one by one. Pass `--light` for a faster pass that skips counter-challenges. |
| `tdd` | Guide test-driven development using red-green-refactor with vertical slices (one test, one implementation, repeat). Includes the prove-it pattern for bug fixes. |
| `write-a-prd` | Create a PRD through user interview, codebase exploration, and deep-module design. Outputs a Markdown PRD file to the project's plans directory, with an optional prompt to publish it as a GitHub issue labeled `epic`. Pass `--no-github` to stay local-only. |
| `prd-to-plan` | Break a PRD into a phased implementation plan using tracer-bullet vertical slices. Outputs a Markdown plan file to the project's plans directory, with an optional prompt to publish it as a sub-issue of the PRD-epic. Accepts a `#N` / issue URL argument to link an existing PRD, or `--no-github` for local-only. |
| `run-plan` | Orchestrate a multi-phase implementation plan by delegating phases to specialized sub-agents (Research, Code, Architect, Debug) with fresh context windows. Accepts a plan file path, a `#N` plan-sub-issue reference, or a full issue URL. Owns the full git/GH ceremony (work branch, per-phase commits, sub-issue sync, PR submission) with opt-out flags (`--no-branch`, `--no-commits`, `--no-github`, `--no-pr`). |
| `commit` | Generate a Conventional Commits message from staged changes and commit. Accepts an optional ticket identifier. |

#### Skill dependencies

Most skills are standalone, but a few read or invoke others at runtime. If you install the skill on the left, you should also install everything on the right to get full functionality:

| Skill          | Depends on     | Why                                                                                                                                                  |
| -------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `run-plan`     | `commit`       | Invokes `/commit` after each phase for per-phase commits. Without it, the commit step fails (unless `--no-commits` is passed).                       |
| `run-plan`     | `tdd`          | Every Code agent brief instructs the agent to read the `tdd` skill. Without it, agents silently skip the TDD workflow.                               |
| `write-a-prd`  | `tdd` _(soft)_ | Reads the `tdd` skill while authoring to shape the PRD's Testing Decisions section. Without it, the PRD still gets written with generic guidance.    |
| `write-a-prd`  | `grill-me` _(soft)_ | Invokes `grill-me` at step 3 to stress-test the design before writing the PRD (skipped if a grilling session already ran in the same conversation). Without it, step 3 is skipped and the PRD relies on whatever design rigor preceded the invocation.    |

`grill-me`, `prd-to-plan`, `tdd`, and `commit` have no skill dependencies and work standalone. The install example at the top of this README lists all six workflow skills — use it as the default for any project that will run the full pipeline.

### Frontend

Skills for client-side projects (React, TypeScript, etc.).

| Skill | Description |
| --- | --- |
| _coming soon_ | |

### Backend

Skills for server-side projects. Stack-agnostic skills apply to any backend; stack-specific skills note their target in the name.

| Skill | Description |
| --- | --- |
| _coming soon_ | |

### ML

Skills for machine learning and data science projects (Python, PyTorch, etc.).

| Skill | Description |
| --- | --- |
| _coming soon_ | |

### Infra

Skills for DevOps, CI/CD, and infrastructure tasks.

| Skill | Description |
| --- | --- |
| _coming soon_ | |

## Repository Structure

```
skills-workflow/
├── README.md
├── universal/          # Language/framework agnostic
│   ├── commit/
│   │   └── SKILL.md
│   └── tdd/
│       └── SKILL.md
├── frontend/           # Client-side (React, TypeScript, etc.)
├── backend/            # Server-side (Kotlin, Node, etc.)
├── ml/                 # Machine learning (Python, PyTorch, etc.)
└── infra/              # DevOps / CI/CD
```

Each skill is a directory containing a `SKILL.md` file with YAML frontmatter (`name`, `description`) and markdown instructions. Supporting files (templates, scripts, reference docs) can live alongside `SKILL.md` in the same directory.

The domain folders (`universal/`, `frontend/`, `backend/`, `ml/`, etc.) are organizational — the CLI discovers skills by their `name` frontmatter, not their directory path. Stack-specific skills should make their target obvious in the skill name (e.g. `ktor-conventions`, `hono-conventions`) rather than relying on directory nesting.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a new skill and the guidelines your contribution should follow.

## Acknowledgments

The following skills were adapted from [Matt Pocock's skills repo](https://github.com/mattpocock/skills):

- `grill-me`
- `prd-to-plan`
- `tdd`
- `write-a-prd`

Many thanks to Matt for sharing his work. He gave an excellent talk about these and other skills at the [AI Engineer - Europe](https://www.youtube.com/watch?v=v4F1gFy-hqg) conference which you should definitely check out if you're reading this. See [docs/UPSTREAM.md](docs/UPSTREAM.md) for a per-skill summary of how our versions have diverged from upstream.
