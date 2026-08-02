# Skills Workflow

A shared library of agent workflow skills. The language below is the orchestration vocabulary the skills (chiefly `run-plan`) use internally — canonical terms first, aliases to avoid after.

## Language

**File-backed research**:
Research whose findings are destined for a `research-<topic>.md` file that later agent briefs point at. The researching agent writes the file itself and returns only a digest plus the path.
_Avoid_: persistent research, heavy research, general-purpose research (that names the worker, not the tier)

**Inline lookup**:
Research whose complete answer fits the ≤8-line digest and has exactly one consumer. Returned inline; no file is ever created.
_Avoid_: narrow lookup, single-fact lookup, Explore research

**Destination rule**:
The tier-selection rule for research: pick by where the findings land (a file that briefs reference → file-backed; a digest with one consumer → inline lookup), decided when the topic is composed — never by predicting output size.
_Avoid_: screenful threshold, size threshold

**Write scope**:
A file-backed research agent's single write authorization: exactly one resolved findings-file path, never repository source. A prompt directive verified by the orchestrator with `git status --porcelain` after the agent returns.
_Avoid_: write permission, sandbox

## Example dialogue

> **Dev:** Phase 2 needs the routing layer mapped — is that an inline lookup?
> **Expert:** Who reads the answer? If the phase brief will point at a research file, it's file-backed by definition — the destination rule doesn't care how small you hope the findings are.
> **Dev:** And "which package manager does this repo use?"
> **Expert:** One fact, one consumer, no file — inline lookup. If the answer somehow comes back as three screens, you misjudged the tier, not the agent.
