source "$FIXTURE_DIR/../../lib.sh"
init_repo
# GitHub's "create a branch" format for issue 123 — SKILL.md step 2.2's
# `<digits>-<slug>` pattern must infer #123 with no ticket argument passed.
git checkout -q -b 123-reconcile-report
stage_feature
