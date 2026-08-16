source "$FIXTURE_DIR/../../lib.sh"
init_repo
# A date at a segment start shape-matches `<digits>-<slug>` but is excluded by
# SKILL.md step 2.2's date rule. Deliberately NOT a branch name the skill text
# names verbatim, so this grades the rule rather than a memorized example.
git checkout -q -b hotfix/2025-11-04-reconcile
stage_feature
