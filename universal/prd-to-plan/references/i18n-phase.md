# i18n Phase Procedure

Load this reference when the PRD introduces or modifies user-facing strings AND the project uses i18n. The SKILL.md gate decides _whether_ to do i18n planning; this file is the _how_.

## Procedure

1. **Discover the i18n setup** — Identify the project's i18n framework, translation file format, supported locales, and key naming conventions by reading existing translation files and configuration.

2. **Audit for reusable keys** — Read translation files for namespaces/scopes likely to overlap with this feature. Do NOT exhaustively read every file — focus on the ones relevant to the feature area. Build a reusable key reference table mapping feature concepts to existing translation calls.

3. **Enumerate new keys** — List every new i18n key needed across all phases, with the default-language copy and the namespace/scope it belongs to. Only do this when the PRD has enough UI specificity (column headers, button labels, status labels, section titles, empty states) to enumerate keys confidently. If the PRD is too vague to determine exact copy, note which areas need keys but defer the specifics to each phase.

4. **Plan a Translations phase** — Include a dedicated "Translations" phase as Phase 1 of the plan. This phase touches only translation files — no source code. It contains: all new keys with default-language values, the reusable key reference table, and the list of translation files to modify. For non-default locales, provide real translated values — do NOT copy default-language strings as placeholders.

5. **Wire up later phases** — All subsequent phases reference translation keys using the project's standard lookup pattern. No translation file edits in later phases. Include the reusable key reference in the plan's architectural decisions section so every phase can consult it.

## Acceptance signal for Step 6 validation

The plan is i18n-correct if:

- Phase 1 is a Translations phase touching only translation files
- Architectural decisions section lists the i18n namespace(s) and reusable-key references
- No later phase edits translation files directly
- Non-default locales have real translations, not placeholder copies of the default
