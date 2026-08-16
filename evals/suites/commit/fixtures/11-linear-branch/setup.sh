source "$FIXTURE_DIR/../../lib.sh"
init_repo
# Linear's default "copy branch name" format: username prefix, lowercase team
# key. SKILL.md step 2.2's lowercase-tracker-key pattern must capture it and
# uppercase the key on output.
git checkout -q -b markus/eng-142-reconcile-report
stage_feature
