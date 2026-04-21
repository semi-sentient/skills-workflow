# Contributing

Thanks for your interest! This repo is a shared library of agent skills designed to work across multiple AI coding harnesses (Claude Code, Cursor, Roo, etc.). New skills, improvements to existing ones, and documentation fixes are all welcome.

## Adding a new skill

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

5. Update the **Available Skills** table in the [README](README.md).
6. Open a PR for review.

## Guidelines

- **Descriptions matter.** The `description` field determines when an agent loads the skill. Be specific about the trigger — "Use when generating React components" is better than "Helps with frontend work."
- **Keep `SKILL.md` under 500 lines.** Move detailed reference material to separate files and reference them from the main skill file.
- **Avoid agent-specific features in shared skills.** Claude Code frontmatter like `allowed-tools`, `context: fork`, and `paths` won't be understood by other agents. If a skill genuinely needs these, note the agent dependency in the description.
- **Test before merging.** Install the skill locally and verify it triggers correctly and produces useful output.
