# Evals

Tooling for one question: **does this change to a skill make it better or worse?**

A skill is a prompt. Editing one is editing a program with no test suite, whose
compiler is stochastic and whose output is a multi-step agent trajectory. That is
why "I think this is an improvement" has been the only available verdict. These
two tiers replace part of that with evidence.

| Tier | What it is | Cost | Time | Proves |
| ---- | ---------- | ---- | ---- | ------ |
| 0 | `lint.py` — static gates over the skill text | free | <1s | You did not break a rule this repo already learned |
| 1 | `run.py` — behavioural fixtures, run headless, graded deterministically | ~$0.20/run | ~20s/run | A named invariant holds, or flipped between two versions |

Neither tier scores "quality". They test **invariants** — the properties a skill
claims about its own behaviour. That is deliberate: of the last fifteen commits
to this repo, almost none were quality judgements. They were behavioural claims
("one question per turn", "a Review agent runs before the commit", "honour the
repo's commitlint config"), and an invariant is cheap to assert and impossible to
argue with.

## Tier 0 — static gates

```bash
./evals/lint.py                      # whole corpus
./evals/lint.py commit run-plan      # named skills
./evals/lint.py --file path/SKILL.md # one file, e.g. an old revision (pre-commit hook)
./evals/lint.py --strict             # warnings are fatal too
```

Errors are structural facts (dead reference link, registration drift, a pinned
model tier). Warnings are heuristics that want a human: an elastic permission
clause, a rule restated in two places, a flag the user docs never mention.

Each rule traces to a specific past regression. The `elastic-permission` and
`restated-rule` rules exist because of `fc60d33`: a permission gated on a
judgement call ("you may bundle 2 (rarely 3) sub-decisions ... when they're
parameters of the same choice") fired far more often than intended, and because
the same carve-out was restated in the `NEVER` list, fixing one site left the
other granting the loophole. Run the linter against the version that shipped that
bug and it flags **both** sites; against the fix, it flags neither.

A heuristic with no way to say "this one is deliberate" becomes noise, and a
noisy gate gets ignored wholesale. So warnings can be suppressed inline, with a
required reason:

```markdown
<!-- lint-ok: elastic-permission — three named conditions, all git-verifiable -->
```

## Tier 1 — behavioural fixtures

```bash
./evals/run.py --dry-run                        # what would run, and the cost
./evals/run.py commit                           # current working tree
./evals/run.py commit --compare HEAD~1 --reps 3 # did my edit help?
./evals/run.py commit --gate                    # CI: nonzero on any failure
```

An **arm** is a skill version: `worktree`, or any git ref. Both arms run the same
fixtures on the same machine in the same session, so model version, harness
build, and machine all cancel — a difference in pass rates is attributable to the
skill diff. Arms are materialised from the canonical `universal/<skill>/` copy,
never from the `.agents/skills/` symlinks, which dangle once extracted alone.

Each run is `claude -p` in a throwaway git repo under `~/.skills-evals/<run-id>/`,
with `--setting-sources project` so only the fixture's own `.claude/` is visible.
Fixture repos are never created inside this repository: the skill under test is
allowed to mutate them freely. They are left on disk after the run so a failure
can be opened and read — `.claude/eval-prompt.txt`, `.claude/final-message.txt`,
`.claude/transcript.jsonl`, and `.claude/outcome.json` are all preserved.

### Assertions see the trajectory, not just the output

Output-only grading cannot see the failures this repo actually ships. Asking
three questions in one turn produces a perfectly good wrap-up document; the
defect is in the *path*. `claude -p` returns a `session_id`, that resolves to a
JSONL transcript, and `harness/trace.py` turns it into an assertable stream of
tool calls — so a fixture can assert on ordering ("a Review agent ran before the
commit"), on abstinence ("never read a source file", "never ran `--no-verify`"),
and on shape ("at most one question per turn").

Write trajectory assertions against the *act*, not a literal string. `git -C
/path diff --cached` is the same act as `git diff --cached`; use
`trace.ran_git("diff --cached")`, which tolerates global options. An assertion
that only matches the bare form reports a false violation the first time an
agent passes `-C` — which is exactly what happened on the first baseline run here.

### Adding a fixture

```
evals/suites/<suite>/fixtures/<name>/
  meta.json    {"skill": "commit", "description": "...", "args": "", "timeout_s": 420}
  setup.sh     runs in a fresh empty dir; builds the repo state
  check.py     def check(ctx, expect) -> None
  prompt.py    optional; default prompt is "/<skill> <args>"
```

`ctx` exposes `.repo`, `.result`, `.json`, `.trace`, `.sh()`, `.read()`,
`.exists()`, `.json_from_result()`. `expect` collects assertions: `.that()`,
`.match()`, `.absent()`, `.equals()`, `.at_most()`, `.at_least()`, and `.info()`
for numbers you want recorded but have no defensible threshold for yet.

Two things the report will tell you about your own fixtures, and both are worth
listening to:

- **unstable** — reps within one arm disagree. Either the fixture is not pinning
  down what it claims, or the skill is genuinely non-deterministic there.
- **non-discriminating** — the assertion passes in both arms every time. It costs
  money on every run and says nothing about the change. Keep it only if it guards
  a regression you think is actually possible.

### Ablation: does this clause earn its place?

A git ref can only compare versions that exist. To test whether a specific
sentence is load-bearing, delete it and re-run:

```bash
./evals/run.py run-plan-review --compare worktree --arm worktree \
  --ablate 'references/agent-operations.md:Adversarial by mandate:.*?not presumed\.'
```

A pattern that matches nothing raises rather than running, because a no-op
ablation would produce two identical arms and a confident "no difference".

## Suites

### `commit` — 11 fixtures, 114 assertions, ~$2.20, ~65s

Fully deterministic grading against the produced commit message: Conventional
Commits shape, Sentence-case default, ticket scope and footer placement,
`commitlint` rules discovered from four different locations, the refuse-on-empty
guard, and the rule that unstaged work must never be described.

`08`–`11` cover ticket inference (SKILL.md step 2): capture from a
GitHub-style issue branch and from Linear's lowercase-key format, the
date-prefix exclusion graded on a branch name the skill text does NOT name
verbatim, and `--no-ticket` beating an inferable branch reference — the
invariant run-plan's local-only mode depends on.

`07-exotic-type-enum` is the discriminating one. Its allowed types are
project-invented (`deliver`, `repair`, `tidy`) and hidden in a `package.json`
key, so no amount of good instinct produces them — the assertion measures whether
the config was actually read rather than whether the message reads well.

### `run-plan-review` — 4 fixtures, 114 assertions at 3 reps, ~$3.50, ~2min

A reconstruction of the July 2026 benchmark, which tested `run-plan`'s Review
gate across paired `clean`/`seeded` worktrees and got 12/12 recall with 12/12
specificity — and was then lost, because the worktrees were torn down and the
numbers lived only in session transcripts.

Two defect classes, each as a clean/seeded pair:

- **bands** — a strict `>` at a boundary the criterion explicitly calls inclusive.
- **wiring** — a component built and unit-tested but never called, the shape of
  bug the original benchmark caught in production.

Both seeded variants keep a **green test suite**. That is the point: a seeded
fixture whose tests fail would never reach a review gate in a real run (the Code
agent's build gate stops it first), so it would be measuring the build gate
instead of the reviewer. Only a criterion-by-criterion read finds these.

The pairing is what makes the numbers mean anything. The seeded arm measures
recall; the clean arm measures false-positive rate. Without the clean arm, any
"improvement" in recall could just be a reviewer that fires more often, and that
is not a stricter gate — it is a broken one.

`seeded_not_met` in `phases.py` records which criteria a defect genuinely
breaks, decided from the defect before looking at any run output. Writing it down
is also what forces each criterion to be unambiguous: an earlier draft put a
band's upper boundary in a second criterion, so one defect broke two criteria and
"correct" was not well defined.

#### The brief is composed from the skill, not stored

`brief.py` extracts the Review role, the adversarial mandate, the diff
instruction, the evidence requirement, and the compactness rule from
`references/agent-operations.md` **in whichever version the arm materialised**,
then fills in the fixture's phase. Edit the Review brief and the prompt this eval
sends changes with it. A frozen copy would measure a snapshot and tell you
nothing about the skill. Extraction is strict — a restructure that hides a block
fails the run rather than quietly sending a brief with a section missing.

Two deliberate compromises, both of which cost coverage:

1. **The output contract is overridden to JSON.** The skill routes the full
   evidence table to a scratch evidence file and returns verdict lines plus
   findings — right for a context-lean orchestrator, wrong for automated
   grading. The original benchmark made the same trade. What it costs: the real
   return split and table format are invisible here.
2. **The brief is tested in isolation, not through `run-plan`.** That is what
   makes it cost cents instead of 400K tokens. What it costs: orchestrator-side
   composition bugs escape entirely. Cover those with `scripts/burn-in.sh`.

Verdict spelling varies between runs (`NOT MET`, `NOT_MET`, `NEEDS-RUNTIME`),
so `common.py` normalises before counting. Long single-line JSON objects are also
occasionally emitted unterminated; the parser closes exactly the outstanding
brackets and records `needed JSON repair to parse` so the lapse stays visible
rather than being papered over.

### `prd-to-plan-criteria` — 2 fixtures, 51 assertions at 3 reps, ~$3.80, ~5min

Tests the **Criteria verifiability** item added to `prd-to-plan`'s Step 6b
checklist after three production plans shipped acceptance criteria that could
not be verified: commands that already passed before the phase ran, commands no
correct implementation could satisfy, non-portable shell, evidence "recorded in
the progress note" (a location `run-plan`'s reviewer cannot read — it cost three
NOT MET verdicts in one run), and human-only criteria without the `Human` prefix
the executing skill's human gate keys on.

One repo, one plan draft, two criteria sets:

- **seeded** — ten criteria, five defective, one per sub-check: a vacuous
  `grep -c … returns 0` against a file the phase never touches; an "exactly 1"
  count the plan's own decisions force to at least 2; GNU-only `stat -c`;
  evidence pasted "into the progress note"; an unlabelled browser check inside a
  `Known risk: human action` phase. Graded on recall (each flagged), precision
  (no sound criterion flagged), and sub-check classification.
- **clean** — the same plan with each defect replaced by a sound counterpart.
  Nothing may be flagged.

The clean arm's gate is `at most 1` flag, not zero. With no real defects to
absorb an adversarial reviewer's energy, roughly one rep in three finds one
defensible quibble in ten sound criteria — while the *same* five sound criteria
are never flagged in the seeded arm, where five real defects soak it up. One
flag is the honest floor of the zero-defect regime; zero as the gate made this
the suite's only unstable cell across every calibration run.

The assertion that distinguishes this suite from a reading-comprehension test is
**execution**: the trace must show the reviewer *ran* the criteria's commands
(`expect_executed` matches distinctive substrings of each command in the Bash
calls). A reviewer that eyeballs `stat -c %s` never learns that BSD `stat` rejects
it; one that runs it does. That is the whole reason the checklist item says
"run every read-only shell command", and it is graded on the act.

Nothing in the plan is implemented when the reviewer runs — `src/bands.js` does
not exist. The brief says so explicitly, so "fails today because the file is
missing" is understood as the *sound* shape of a criterion, and only "passes
today" or "cannot pass after" is a defect. Without that sentence the suite
would grade the reviewer's patience with missing files, not its judgement.

`plan.py` is the single source of the plan text: `setup.sh` renders it to disk
and `check.py` grades against the same lists, so the criteria the reviewer reads
and the criteria the grader expects cannot drift apart.

The brief is composed from the skill under test — the Step 6b block and Step
6a's reviewer instruction are extracted from `SKILL.md` per arm — so the natural
ablation is the item itself:

```bash
./evals/run.py prd-to-plan-criteria --compare worktree --arm worktree \
  --ablate 'SKILL.md:- \*\*Criteria verifiability\*\*.*?not just one\.\n'
```

Result (2026-08-30, 3 reps): **4 regressions.** Seeded recall 3/3 → 0/3 (every
ablated rep missed the vacuous already-passes seed — the others are caught by
generic reviewer instinct, that one only by the item), sub-check classification
3/3 → 0/3 (findings misattributed to "source accuracy"), seeded-arm precision
3/3 → 1/3, and the clean arm's quibble rate worsened. The clause earns its place.

A calibration lesson worth keeping: the first ablation A/B measured **no
difference**, because the suite's own output contract enumerated the sub-check
names and defined `today` as "what the command returned when you ran it" — the
JSON schema leaked the ablated item's whole mandate back into the brief. The
contract is now mandate-neutral (`failed` is stated "in the checklist's own
words") and classification is graded from the reviewer's free text. When a
fixture's output contract restates what the skill text is supposed to cause,
the eval measures the contract.

A second lesson: the reviewer beat the fixture, four rounds running. The first
"clean" criteria sets contained a vacuous byte-size bound, a browser check the
plan's own decisions made unsatisfiable, a `# pass N` literal Node's reporter
never prints, and an uncountable per-station claim with no station set defined —
every one a defensible flag. The Criteria verifiability item catches exactly the
class of defect its own eval author kept writing.

### Dialogue fixtures — grading an interview

An interview skill's contract is about what it does with the *answers*, so one
`claude -p` call cannot grade it. A fixture with `"mode": "dialogue"` in
`meta.json` runs the skill as a resumable session and plays the user from the
fixture's `persona.md` with a second, tool-less `claude -p` session
(`harness/dialogue.py`). The opening message is `/<skill>` plus `plan.md`.

The persona is a hidden ground truth with planted defects — a claim the code
contradicts, a term used two ways, a "figure it out later" dodge, a decision
with a known flaw the user holds until the flaw is *named* — and a fixed event
vocabulary (`dodge_pressed:webhooks`, `challenged:store`). The simulator is
scripted, not judging: it answers what it is asked and emits an event when its
trigger fires. `check.py` grades the events, the final wrap-up, the files the
skill wrote, and the trajectory. `ctx.dialogue` exposes the turns and events;
`.claude/dialogue.json` in the fixture repo has the whole exchange.

`evals/suites/grilling/common.py` separates two kinds of assertion on purpose.
*Recall* (asked the planted question, surfaced the contradiction, pressed the
dodge, never asked the user for a fact the repo holds) is what both grilling
lineages claim. *Rigour* (pushed back on the flawed answer, wrap-up separates
assumptions from decisions) is what our fork added; upstream failing those is
the finding, not a suite bug. Turn counts and questions-per-turn are recorded
as info, never graded — round-based and one-at-a-time interviewing trade those
off deliberately, and the number is for reading, not for a verdict.

Dialogue runs cost 10-30× a single run and take 10-40 minutes each. Keep
`--jobs` at 4 and `--reps` at 1 until the fixture is known to close cleanly
(`interview reached a close` passes), then go to 3.

### Path arms — benchmarking against a skill outside this repo

`--arm path:<dir>` or `--compare path:<dir>` materialises a skill from any
directory tree searched for `<skill>/SKILL.md` — an upstream clone, say — and
labels the arm with that repo's short SHA. A fixture's `"companions"` list
names skills the one under test may delegate to (`grilling`,
`domain-modeling`); they are materialised from the same arm when that arm has
them and skipped when it does not, so a dispatcher-style skill resolves its
target and a self-contained one is not penalised for lacking a file it never
mentions. `--compare` is repeatable; each baseline is compared against the
candidate.

## Baselines

`evals/baselines/*.json` holds a compact, diffable record of the last recorded
run per suite: per-assertion pass counts, cost, model, and how each arm resolved.

```bash
./evals/run.py commit --reps 3 --baseline-out evals/baselines/commit.json
```

Commit these. Their absence is the reason the July 2026 results could not be
built on: the measurement was made, and then there was nothing for the next
change to be compared against.

## What this cannot prove

**End-to-end `run-plan` quality.** At ~400K tokens and 30–60 minutes per run,
the 25–30 paired trials needed to separate a 75% win rate from a coin flip is
over 20 hours and ~20M tokens. Don't attempt it. Convert `run-plan`'s claims into
invariants, unit-test its briefs the way `run-plan-review` does, and use
`scripts/burn-in.sh` for the cold structural paths.

**Anything subjective.** "Is this PRD better" needs a paired blind comparison
with randomised order, stripped provenance, a rubric fixed before any output is
seen, and enough trials to matter. That is a Tier 2 tool and it does not exist
here yet.

**That a passing suite means a good skill.** These fixtures test what someone
thought to assert. An all-green run against a change means either the change is
behaviourally inert on these fixtures, or nothing covers what it touched — the
report says exactly that rather than claiming a win. When it does, the useful
move is to add a fixture that targets the change, not to trust the green.

## Two findings from standing this up

**The `commit` skill's commitlint-detection step is not load-bearing on Opus 5.**
Comparing the current skill against `481dd26^` — a version that never mentions
commitlint — all 39 assertions passed in both arms across 2 reps, including
`looked for repo commit-message rules`. Even `07-exotic-type-enum`, with
invented types hidden in a `package.json` key, passed 2/2 on the old version. The
model reads repo conventions unprompted. This is evidence for trimming that step,
not a mandate: it may still matter on a weaker model, and n=2 is thin.

**The adversarial mandate costs ~60% more output tokens for no measurable
detection gain on these two defect classes.** Ablating it (3 reps, 8 cells)
produced 1 improvement and 1 regression — both single-rep flips, i.e. noise —
while output tokens fell from ~2340 to ~1470 per run. Recall and specificity were
unchanged. Worth more defect classes before acting on it; a boundary error and a
missing wiring call are both fairly legible, and the mandate may earn its keep on
subtler bugs.
