# skills-workflow

Agent skills workflow with an emphasis on orchestration during execution that works across Claude Code, Cursor, Roo, and other agent harnesses.

## Recommended Workflow

These skills are designed to chain together. See [WORKFLOW.md](WORKFLOW.md) for a guided walkthrough of the full idea-to-implementation workflow using `grill-me` → `write-a-prd` → `prd-to-plan` → `run-plan`.

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
| `commit` | Generate a Conventional Commits message from staged changes, preview it, and commit after confirmation. Accepts an optional ticket identifier. |
| `grill-me` | Stress-test a plan or design through relentless questioning, resolving each branch of the decision tree one by one. |
| `prd-to-plan` | Break a PRD into a phased implementation plan using tracer-bullet vertical slices. Outputs a Markdown plan file to the project's plans directory. |
| `run-plan` | Orchestrate a multi-phase implementation plan by delegating phases to specialized sub-agents (Research, Code, Architect, Debug) with fresh context windows. Takes a plan file path as argument. |
| `tdd` | Guide test-driven development using red-green-refactor with vertical slices (one test, one implementation, repeat). Includes the prove-it pattern for bug fixes. |
| `write-a-prd` | Create a PRD through user interview, codebase exploration, and deep-module design. Outputs a Markdown PRD file to the project's plans directory. |

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

### Adding a new skill

1. Choose the appropriate domain folder (or create one if none fits).
2. Create a new directory with a descriptive, kebab-cased name.
3. Add a `SKILL.md` with valid frontmatter:

```yaml
---
name: my-new-skill
description: A clear, concise description of what this skill does and when to use it. Front-load the key use case — descriptions longer than 250 characters may be truncated.
---

Your skill instructions here...
```

4. Register the skill in the agent discovery directories. The `skills` CLI discovers skills from `.agents/skills/` and `.claude/skills/` — the domain folders (`universal/`, `frontend/`, etc.) are for organization only and are not scanned directly. Run the registration script, which auto-detects the domain and creates the required symlinks:

```bash
./scripts/register-skill.sh <skill-name>
```

5. Update the **Available Skills** table in this README.
6. Open a PR for review.

### Guidelines

- **Descriptions matter.** The `description` field determines when an agent loads the skill. Be specific about the trigger — "Use when generating React components" is better than "Helps with frontend work."
- **Keep `SKILL.md` under 500 lines.** Move detailed reference material to separate files and reference them from the main skill file.
- **Avoid agent-specific features in shared skills.** Claude Code frontmatter like `allowed-tools`, `context: fork`, and `paths` won't be understood by other agents. If a skill genuinely needs these, note the agent dependency in the description.
- **Test before merging.** Install the skill locally and verify it triggers correctly and produces useful output.
