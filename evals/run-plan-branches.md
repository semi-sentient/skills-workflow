# run-plan branch register

`run-plan` has branches a normal run never reaches — a repo with a PR bot never
executes `gh pr create`, a plan created by `prd-to-plan` never exercises
standalone `gh-issue:` resolution. Those paths go cold silently, and the first
time anyone notices is when a user hits one.

This register is the shrinking list. It records which branch has been exercised,
by what, and when — so "we think that path is cold" becomes a fact rather than a
hunch. Update it after any run that reaches a new branch.

It lives here rather than in a fixture's `BURN-IN.md` because fixtures are
single-use and get torn down; the coverage record has to outlive them.

## How a branch gets covered

| Instrument | Good for | Cost |
| ---------- | -------- | ---- |
| `evals/run.py` Tier 1 fixture | deterministic branches that abort before any sub-agent | ~$0.20, ~20s |
| `scripts/burn-in.sh` probe | resolution branches needing real git/`gh` state | seconds, no tokens |
| `scripts/burn-in.sh` full run | irreversible git/GH paths end to end | ~300-500K tokens, 30-60 min |
| A production run | everything, with perfect environment fidelity | free, but only covers the paths your repos take |

## Register

Status as of the 2026-07-27 burn-in (fixture `burnin-2026-07-27`, silent repo)
plus the declared-path validation in a production repo.

| Branch | Instrument | Status |
| ------ | ---------- | ------ |
| Step 1b — `gh-sub-issue:` match | production run | exercised |
| Step 1b — `gh-issue:` standalone plan | burn-in probe + full run | exercised ×3 |
| Step 1b — stale footer on a non-plan (resolvable) | `probe stalefooter` | exercised ×2 |
| Step 1b — genuine tie, two plans one issue | `probe tie` | exercised ×2 |
| Step 1b — PRD guard, nothing survives the discard | `probe guard` | exercised ×1 — impure, see note |
| Step 1b — fetch-from-GH fallback (no local file) | — | **cold** |
| Step 1b.1 — no parent epic, `<gh_issue_number>` unset | burn-in full run | exercised |
| Step 1c — local ahead of GH, pre-confirmation push | — | **cold** |
| Step 1e.2 — interrupted-phase detection | — | **cold** |
| Step 4.5 — scoped re-review exception | — | **cold** |
| Step 4.7 — pre-commit hook failure → Debug | — | **cold** |
| Step 5d — declared: poll + `gh pr edit` | production run | exercised |
| Step 5d — declared: poll timeout, report-and-wait | — | **cold** |
| Step 5d — silent: `gh pr create` | burn-in full run | exercised |
| Step 5d — `Refs #` omitted, no parent epic | burn-in full run | exercised |
| Step 5d — provenance footer omitted on silent path | burn-in full run | exercised |
| Step 5a — degraded sync reconciliation | — | **cold** |
| Step 5e — plan file cleanup on complete | burn-in full run | exercised |
| Outcome `partial` / `aborted` | — | **cold** |
| `commit` — `Ticket:` footer with leading blank line | burn-in full run + production | exercised |

### Notes

- **The PRD guard result is impure.** `probe guard` passes `#999999`, which does
  not exist on GitHub, so the failure conflates "no such issue" with "the only
  local match is a PRD". The transcript showed the discard logic genuinely firing,
  so it is evidence — but a clean test would publish the PRD as a real issue and
  pass that number. Worth fixing when the probe is next regenerated.
- **Step 1b resolution is the best Tier 1 candidate in the skill.** It is
  deterministic, aborts before any sub-agent, has no side effects, and has already
  demonstrated real run-to-run variance — the original tie-break rule resolved two
  ways across three reps, which is what exposed it. Promoting these three probes
  to fixtures would make them free to re-run on every future edit to Step 1b.
- **Cold is not the same as broken.** Most rows above are cold because reaching
  them requires deliberately breaking something (revoking auth mid-run, killing a
  run between checkbox and commit). Rank them by what a user actually hits: the
  fetch-from-GH fallback is common, the degraded-sync path is not.
