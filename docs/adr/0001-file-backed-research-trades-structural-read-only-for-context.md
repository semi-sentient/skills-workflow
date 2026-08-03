# File-backed Research trades the structural read-only guarantee for orchestrator context

`run-plan`'s Research mode was pinned to a read-only worker (`Explore`), which physically cannot write files — so every findings block returned inline and the orchestrator persisted it, landing the content in the orchestrator's context twice (once on return, once as its own Write input) and keeping it resident for the rest of the run (~26–32K tokens on measured multi-topic runs). We split Research into two tiers — **file-backed** (`general-purpose`: the agent writes `research-<topic>.md` itself and returns only a ≤8-line digest plus the path) and **inline lookup** (`Explore`, kept for digest-sized answers with a single consumer) — accepting that the file-backed tier's read-only-toward-the-repo property degrades from a structural guarantee to conduct: a hard singular Write Scope brief section, backed by an orchestrator `git status --porcelain` check after every file-backed return.

## Considered Options

- **Keep Research pinned to `Explore`** — preserves the structural guarantee, keeps the double-transit cost. Rejected: a polluted orchestrator context is re-charged on every later turn, while the guarantee it buys is one the skill already does without elsewhere (Review mode is read-only by conduct on `general-purpose`).
- **Prompt promise with no verification** — rejected: the backstop costs one trivial git command per research return, and Step 1e.2's clean-tree invariant makes it airtight for upfront research; without it, a stray write surfaces later as Review-agent "scope creep" misattributed to the Code agent.
- **Size-threshold tier selection** ("more than a screenful") — rejected: output size is unknowable at spawn time. The tier is picked by the findings' **destination** (file-destined → file-backed; digest-with-one-consumer → inline lookup), which is decidable when the topic is composed.

## Consequences

- File-backed research emits `<usage>`, so research rows in the run ledger carry real token/duration figures instead of `n/a`.
- Research token spend rises (`general-purpose` vs `Explore`) — the intended trade: transient subagent cost for permanent orchestrator occupancy.
- Watch item — **resolved 2026-08-02**: a blinded three-topic, two-judge experiment in a consumer repo found no `Explore` search-quality advantage to preserve. An earlier single-probe gap favoring `Explore` was explained by its breadth directive, not the agent type: `general-purpose` with an explicit "search breadth: very thorough" directive beat `Explore` in 3 of 3 topics on independently verified unique facts (+~5% research tokens). That directive is now part of the file-backed brief's Write Scope & Search Breadth section. The same experiment showed digests reliably dropped discovered hazards (1/6 decisive facts reached the digest), so the digest contract now requires hazards to lead.
