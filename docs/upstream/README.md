# Upstream sync ledgers

One file per skill that was forked from [mattpocock/skills](https://github.com/mattpocock/skills). Each file pins the upstream path(s) and the last upstream commit reviewed, so the next sync is mechanical rather than archaeological.

[UPSTREAM.md](../UPSTREAM.md) remains the index and holds the skills that have not been migrated to a per-skill ledger yet.

## Ledger format

```markdown
# <skill>

**Upstream path(s):** `skills/<domain>/<name>` (+ any skill it now delegates to)
**Last reviewed upstream commit:** `<sha>` (<date>)

## Current divergence
What ours does that upstream does not, and vice versa. Rewritten on each sync.

## Sync ledger
### <date> — reviewed `<from>..<to>`
- adopted: ...
- rejected: ... (why)
- deferred: ... (what would change the answer)
```

Upstream paths move (`write-a-prd` → `to-spec`, `grill-me`'s body → `grilling`), so the path list is part of the pin: a rename that is not recorded here is the reason a sync gets skipped.

## Syncing a skill

```bash
git clone --depth=200 https://github.com/mattpocock/skills /tmp/upstream-skills
scripts/upstream-log.sh grill-me /tmp/upstream-skills   # commits since the pin, on the pinned paths
```

Then for each commit: adopt, reject with a reason, or defer with the condition that would change the answer. Record all three. Update the pin and the **Current divergence** section, run `./evals/lint.py <skill>`, and — when a behavioural claim changed — `./evals/run.py <suite> --compare HEAD`.

A sync that adopts nothing still gets a ledger entry: "reviewed, nothing adopted" is what tells future-us the gap was looked at, not overlooked.
