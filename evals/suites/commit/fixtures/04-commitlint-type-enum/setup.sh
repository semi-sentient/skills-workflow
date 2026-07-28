source "$FIXTURE_DIR/../../lib.sh"
init_repo
cat > .commitlintrc.json <<'CFG'
{
  "rules": {
    "type-enum": [2, "always", ["feat", "fix"]],
    "header-max-length": [2, "always", 60],
    "subject-case": [2, "always", "sentence-case"],
    "scope-empty": [2, "never"]
  }
}
CFG
git add -A
git commit -q -m "chore: Add commitlint rules"
stage_feature
