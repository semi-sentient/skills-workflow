# Contributing

Thanks for your interest! This repo is a shared library of agent skills designed to work across multiple AI coding harnesses (Claude Code, Cursor, Roo, etc.). New skills, improvements to existing ones, and documentation fixes are all welcome.

## Adding a new skill

1. Choose the appropriate domain folder (or create one if none fits). Domain folders (`universal/`, `frontend/`, `backend/`, `ml/`, `infra/`) are organizational only — the CLI discovers skills by their `name` frontmatter, not their directory path. Stack-specific skills should encode the target in the skill name (e.g. `ktor-conventions`, `hono-conventions`) rather than relying on directory nesting.
2. Create a new directory with a descriptive, kebab-cased name.
3. Add a `SKILL.md` with valid frontmatter:

```yaml
---
name: my-new-skill
description: A clear, concise description of what this skill does and when to use it. Front-load the key use case, and name the phrases a user would actually type.
---
Your skill instructions here...
```

4. Register the skill in the agent discovery directories, so agents working *in this repo* can invoke it. Run the registration script, which auto-detects the domain and creates the required symlinks:

```bash
./scripts/register-skill.sh <skill-name>
```

   The discovery directories (`.agents/skills/`, `.claude/skills/`) are gitignored — they exist for local use only and are never committed. Regenerate them after a fresh clone with `./scripts/register-skill.sh --all`. Consumers install straight from the domain folders; see [Why the discovery directories are not committed](#why-the-discovery-directories-are-not-committed).

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

### Why the discovery directories are not committed

They used to be, and it silently broke every consumer.

A committed symlink gives the `skills` CLI two paths to one skill: the real file under `universal/`, and the symlink under `.agents/skills/`. The CLI searches agent directories first, so it recorded the symlink path — then hashed the directory by reading its *files*, found none (a symlink is not a file), and wrote `e3b0c442…b855`, the SHA-256 of the empty string. Every lock file in every consuming repo verified nothing.

Updates broke too, and more visibly. `skills update` re-discovers the source repo, finds the same skill at three paths, and refuses:

> Warning: Multiple current paths match these skills from …; skipping them rather than deleting or migrating the wrong skill

That is why `npx skills@latest update` stopped picking up changes.

Keeping the discovery directories out of git leaves exactly one path per skill. Consumers get `universal/<name>/SKILL.md` and a real digest; existing lock files migrate themselves on the next update.

### Proving a change is an improvement

A skill is a prompt, so an edit has no compiler and no test suite to fall back on. [`evals/`](evals/README.md) provides two gates; which one a change needs depends on what kind of change it is.

| Change | Gate |
| ------ | ---- |
| Any edit at all | `./evals/lint.py` — free, sub-second |
| A behavioural rule (turn structure, ordering, a refusal, a detected convention) | A Tier 1 fixture asserting it, then `./evals/run.py <suite> --compare HEAD --reps 3` |
| A `run-plan` agent brief | `./evals/run.py run-plan-review --compare HEAD --reps 3` |
| Deleting a clause you suspect is dead weight | `./evals/run.py <suite> --compare worktree --arm worktree --ablate '<file>:<regex>'` |
| Mechanical metrics (token footprint, call counts) | A deterministic estimate beats a noisy experiment — write the arithmetic down; `evals/harness/context_tally.py <transcript>` measures a real run |
| Shell a skill ships (`run-plan`'s `references/rp.sh`) | `./evals/deterministic/test-rp-sh.sh` — no model, sub-second |
| `run-plan`'s orchestrator loop (brief shape, file brokering, review-before-commit, peak context) | `./evals/run.py run-plan-orchestrator --reps 1` — one end-to-end dialogue run, ~$5–15 |
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

The fixture is single-use (a complete run leaves checked criteria, a pushed branch and an open PR, so a re-run resolves as a resume) and a full run spends real sub-agent tokens, so regenerate rather than reset. `BURN-IN.md` inside the fixture holds the observation checklist; the durable coverage record is [`evals/run-plan-branches.md`](evals/run-plan-branches.md) — update it after any run that reaches a new branch.

## Guidelines

- **Descriptions matter.** The `description` field determines when an agent loads the skill. Be specific about the trigger — "Use when generating React components" is better than "Helps with frontend work."
- **Keep `SKILL.md` under 500 lines, 50 KB, and 7,000 words** (`evals/lint.py` enforces all three). `SKILL.md` is injected verbatim on every invocation and re-paid after every compaction, so its size is resident context for the whole run — a line cap alone was passed by writing paragraphs, which is how `run-plan` reached 102 KB at 480 lines. Move procedure that only some runs exercise into a `references/` file loaded when its trigger fires (see `universal/run-plan/references/` for the pattern: each file opens with the condition that loads it), and link to it from the main skill file. A new mechanism must displace text or live in a reference.
- **Avoid agent-specific features in shared skills.** Claude Code frontmatter like `allowed-tools`, `context: fork`, and `paths` won't be understood by other agents. If a skill genuinely needs these, note the agent dependency in the description.
- **Test before merging.** Install the skill locally and verify it triggers correctly and produces useful output.
