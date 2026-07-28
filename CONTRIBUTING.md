# Contributing

Thanks for your interest! This repo is a shared library of agent skills designed to work across multiple AI coding harnesses (Claude Code, Cursor, Roo, etc.). New skills, improvements to existing ones, and documentation fixes are all welcome.

## Adding a new skill

1. Choose the appropriate domain folder (or create one if none fits). Domain folders (`universal/`, `frontend/`, `backend/`, `ml/`, `infra/`) are organizational only — the CLI discovers skills by their `name` frontmatter, not their directory path. Stack-specific skills should encode the target in the skill name (e.g. `ktor-conventions`, `hono-conventions`) rather than relying on directory nesting.
2. Create a new directory with a descriptive, kebab-cased name.
3. Add a `SKILL.md` with valid frontmatter:

```yaml
---
name: my-new-skill
description: A clear, concise description of what this skill does and when to use it. Front-load the key use case — descriptions longer than 250 characters may be truncated.
---
Your skill instructions here...
```

4. Register the skill in the agent discovery directories. The `skills` CLI discovers skills from `.agents/skills/` and `.claude/skills/` — the domain folders are not scanned directly. Run the registration script, which auto-detects the domain and creates the required symlinks:

```bash
./scripts/register-skill.sh <skill-name>
```

5. Update the **Available Skills** table in the [README](README.md).
6. If the new skill reads or invokes another skill at runtime, add a row to the **Skill dependencies** table in the README so installers know what else to pull in.
7. If the skill fits into the `grill-with-docs` (or `grill-me`) → `write-a-prd` → `prd-to-plan` → `run-plan` chain, update [docs/WORKFLOW.md](docs/WORKFLOW.md) to reflect its place in the flow.
8. Open a PR for review.

## Modifying an existing skill

If you add, rename, or remove a top-level file or directory inside a skill (for example, introducing a `references/` folder, or moving content out of `SKILL.md`), re-run the registration script for that skill:

```bash
./scripts/register-skill.sh <skill-name>
```

The script is idempotent: it adds missing symlinks and prunes dangling ones in `.agents/skills/<skill-name>/` and `.claude/skills/<skill-name>/`. Edits to the contents of an already-linked file don't require a re-run — the symlinks resolve to the source.

### Proving a change is an improvement

A skill is a prompt, so an edit has no compiler and no test suite to fall back on. [`evals/`](evals/README.md) provides two gates; which one a change needs depends on what kind of change it is.

| Change | Gate |
| ------ | ---- |
| Any edit at all | `./evals/lint.py` — free, sub-second |
| A behavioural rule (turn structure, ordering, a refusal, a detected convention) | A Tier 1 fixture asserting it, then `./evals/run.py <suite> --compare HEAD --reps 3` |
| A `run-plan` agent brief | `./evals/run.py run-plan-review --compare HEAD --reps 3` |
| Deleting a clause you suspect is dead weight | `./evals/run.py <suite> --compare worktree --arm worktree --ablate '<file>:<regex>'` |
| Mechanical metrics (token footprint, call counts) | A deterministic estimate beats a noisy experiment — write the arithmetic down |
| Irreversible git/GH paths | `./scripts/burn-in.sh` (below) |

```bash
./evals/lint.py                                  # every skill, all rules
./evals/run.py --dry-run                         # what would run, and the cost
./evals/run.py commit --compare HEAD --reps 3    # did the edit help?
```

Two rules of thumb worth internalising. An **all-green comparison is not a win** — it means either the change is behaviourally inert or no fixture covers what it touched, and the report says so explicitly; the move is to add a fixture that targets the change. And **record the baseline** (`--baseline-out evals/baselines/<suite>.json`) and commit it, so the next change has something to be compared against.

### Burning in `run-plan`

`run-plan` drives irreversible git and GitHub operations, and several of its branches — standalone plan resolution, the `gh pr create` submission path, the PRD guard — are never reached by a normal run. After changing it, build a throwaway fixture repo rigged to walk those paths:

```bash
./scripts/burn-in.sh setup <fixture-name>   # creates a private GitHub repo; prints the invocation
./scripts/burn-in.sh verify <fixture-name>  # checks the outcomes after you run it
```

The fixture is single-use (a complete run deletes its own plan file) and a full run spends real sub-agent tokens, so regenerate rather than reset. `BURN-IN.md` inside the fixture holds the observation checklist; the durable coverage record is [`evals/run-plan-branches.md`](evals/run-plan-branches.md) — update it after any run that reaches a new branch.

## Guidelines

- **Descriptions matter.** The `description` field determines when an agent loads the skill. Be specific about the trigger — "Use when generating React components" is better than "Helps with frontend work."
- **Keep `SKILL.md` under 500 lines.** Move detailed reference material into a `references/` subfolder next to `SKILL.md` (see `universal/tdd/references/` and `universal/run-plan/references/` for examples) and link to it from the main skill file.
- **Avoid agent-specific features in shared skills.** Claude Code frontmatter like `allowed-tools`, `context: fork`, and `paths` won't be understood by other agents. If a skill genuinely needs these, note the agent dependency in the description.
- **Test before merging.** Install the skill locally and verify it triggers correctly and produces useful output.
