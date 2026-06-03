---
name: write-a-prd
description: Create a PRD through user interview, codebase exploration, and module design, saved as a local Markdown file and optionally published as a GitHub issue with the `epic` label. Use when user wants to write a PRD, create a product requirements document, or plan a new feature. Pass `--no-github` to skip the publish prompt.
---

This skill will be invoked when the user wants to create a PRD. You may skip steps if you don't consider them necessary.

1. Ask the user for a long, detailed description of the problem they want to solve and any potential ideas for solutions.

2. Explore the repo to verify their assertions and understand the current state of the codebase.

3. If a grilling session has already been conducted in this conversation and its wrap-up covered the decision space needed for the PRD, skip this step. Otherwise, read and run a grilling skill on the plan: prefer `grill-with-docs` if it's available (it adds inline `CONTEXT.md` updates and ADR offers on top of the same interview engine), and fall back to `grill-me` if not. Pass `--light` if a quick pass is sufficient; otherwise run the full protocol. If neither skill is installed, skip this step.

4. Sketch out the major modules you will need to build or modify to complete the implementation. Actively look for opportunities to extract deep modules that can be tested in isolation.

A deep module (as opposed to a shallow module) is one which encapsulates a lot of functionality in a simple, testable interface which rarely changes.

Check with the user that these modules match their expectations. Check with the user which modules they want tests written for.

5. Read the `tdd` skill and incorporate its testing philosophy into the PRD's Testing Decisions section. Specifically, ensure the PRD specifies:
   - TDD red-green-refactor workflow using vertical slices (one test → one implementation → repeat), not horizontal slices (all tests first, then all implementation)
   - Tests verify behavior through public interfaces, not implementation details
   - Which behaviors each module should be tested for (not implementation steps)
   - Before recommending test scope, read the project's testing conventions doc and align the recommendation with the project's coverage threshold and per-file test-density rule

6. Once you have a complete understanding of the problem and solution, use the template below to write the PRD.

   **Step 6a — Determine the plans directory** using this precedence:
   1. If `.agents/plans/` exists, use it
   2. Else if `.claude/plans/` exists, use it
   3. Else if `.agents/` exists, create `.agents/plans/` and use it
   4. Else if `.claude/` exists, create `.claude/plans/` and use it
   5. Otherwise, create `.plans/` and use it

   Compute the target path as `<plans-dir>/<slug>-prd.md`. Derive `<slug>` from the feature name by:
   1. Lowercase
   2. Replace spaces with hyphens
   3. Strip any character that is not alphanumeric or a hyphen
   4. Collapse any run of consecutive hyphens to a single hyphen; trim leading/trailing hyphens

   Examples:
   - "User Onboarding" → `user-onboarding-prd.md`
   - "MUI v9 Migration" → `mui-v9-migration-prd.md`
   - "User Onboarding (v2)" → `user-onboarding-v2-prd.md`

   `prd-to-plan` applies the same slugify rule when pairing the plan filename to this PRD (producing `<slug>-plan.md`), so consistency here is load-bearing for re-invocation detection to work across the two skills.

   **Step 6b — Re-invocation detection** (run before writing):

   Check for existing state:
   - Does the target PRD file already exist at the computed path?
   - If GH integration is in scope (Step 7's preconditions met): does the existing local file carry a `<!-- gh-issue: N -->` footer indicating it has been published?

   Branch based on state:

   | Local file | GH issue | Prompt                                                                                                                 |
   | ---------- | -------- | ---------------------------------------------------------------------------------------------------------------------- |
   | No         | No       | Proceed normally                                                                                                       |
   | Yes        | No       | `PRD file exists at <path>. Overwrite (regenerate from interview) / publish existing file as a new GH issue / cancel?` |
   | Yes        | Yes      | `PRD file exists at <path> and is published as GH issue #N. Overwrite local + update GH / cancel?`                     |

   Branch behavior:
   - **Overwrite (regenerate)** → proceed to Step 6c (re-run interview steps 1–5 first if needed; then write fresh content)
   - **Publish existing as new GH issue** → skip Step 6c entirely (file is already authored); jump straight to Step 7 using the existing file
   - **Overwrite local + update GH** → proceed to Step 6c, then Step 7's update path (7e)
   - **Cancel** → stop

   **Step 6c — Write the PRD** using the template below. The `> GH Issue:` header is omitted on the first write (no issue exists yet); it's added by Step 7 after publish (or carried forward from the prior file content if updating an already-published PRD).

<prd-template>

# PRD: <Feature Name>

> GH Issue: <only present after Step 7 publishes; format: `#N — https://github.com/<org>/<repo>/issues/N`>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions
- User-facing terminology: when the feature includes UI, list the specific labels, column headers, status values, button text, section titles, and empty-state messages that will appear. This specificity enables the plan to define translation keys upfront rather than inventing copy during implementation.

Do NOT include specific file paths or code snippets unless they are immune to code changes. They may end up being outdated very quickly.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this PRD.

## Further Notes

Any further notes about the feature.

<!--
  If published as a GH issue, Step 7 appends a footer line at the very end
  of the file using an HTML comment of the form:  gh-issue: <issue_number>
  This marker is used by re-invocation detection and by `prd-to-plan` to find
  the linked PRD-epic when this PRD is referenced as the parent.
-->

</prd-template>

---

7. **Publish to GitHub** (only if GH integration is in scope — see preconditions below)

   **Step 7 — Preconditions** (skip the entire step if any fail):
   - The user did NOT pass `--no-github` to this skill invocation
   - `git remote get-url origin` returns a `github.com` URL
   - `gh auth status` reports authenticated
   - Capture `<org>/<repo>` from the remote URL

   If any precondition fails, the PRD remains local-only — no error, just stop here.

   **Step 7a — Confirmation gate:**

   Report: `PRD written to <path>. Review the file (and edit if needed), then reply 'publish' to create a GitHub issue with label 'epic', or 'cancel' to keep it local.`

   Wait for explicit confirmation. The user may edit the file before confirming.

   **Step 7b — Create the GitHub issue:**

   First ensure the `epic` label exists, since `gh issue create --label epic` fails with HTTP 422 if it doesn't:

   ```bash
   gh label create epic \
     --color 5319e7 \
     --description "Product requirements, user stories, and acceptance criteria for new features" \
     2>/dev/null || true
   ```

   This is idempotent: `gh label create` errors when the label already exists, and `2>/dev/null || true` swallows that so a pre-existing `epic` label (with whatever color/description the repo already chose) is left untouched. Do NOT add `--force` — that would overwrite an existing label's color/description. If this command fails for a real reason (auth, network), the `gh issue create` below surfaces it. Then create the issue:

   ```bash
   gh issue create \
     --title "PRD: <feature_name>" \
     --body-file <plan_file_path> \
     --label epic
   ```

   Capture the new issue number and URL from the output.

   Prefix the issue title with `PRD: ` so epics are scannable in the issues list, and so the issue title matches the document's `# PRD: <Feature Name>` heading. This is a **display prefix only**: the slug and feature-name derivation in Step 6a stay on the *bare* feature name, and `prd-to-plan` strips the `PRD: ` prefix when deriving the plan slug, plan heading, and sub-issue title from this epic. No Conventional-Commits *type* prefix either — PRDs are top-level epics, not constrained by the commit-type convention.

   **Step 7c — On success:**
   1. Append `<!-- gh-issue: <issue_number> -->` as a footer to the local PRD file
   2. Update the `> GH Issue:` header line at the top of the file with the issue reference: `> GH Issue: #<n> — https://github.com/<org>/<repo>/issues/<n>`
   3. Report the issue URL to the user

   **Step 7d — Failure handling:**
   - **Create fails** (network, auth, permission, etc.): the local file is intact. Report the error verbatim and tell the user to re-run `/write-a-prd` once the issue is resolved — Step 6b's re-invocation matrix will detect the existing file and offer the **"publish existing file as a new GH issue"** option, which skips re-authoring and only retries the publish.

   **Step 7e — Update path** (when Step 6b's re-invocation chose "Overwrite local + update GH"):

   Instead of `gh issue create`, run:

   ```bash
   gh issue edit <existing_issue_number> --body-file <plan_file_path>
   ```

   This replaces the issue body wholesale, preserving the issue number, comment history, and any sub-issue relationships (e.g., plans created via `prd-to-plan` that reference this PRD as their parent stay linked). The `<!-- gh-issue: <n> -->` footer is already present in the file from the original publish — do NOT re-append. On success, just report the issue URL.
