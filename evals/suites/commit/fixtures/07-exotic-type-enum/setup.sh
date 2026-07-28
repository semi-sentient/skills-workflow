source "$FIXTURE_DIR/../../lib.sh"
init_repo

# Two things make this fixture discriminating where 03 and 04 are not:
#   1. The config lives in a package.json key, not a commitlint.config.* file
#      sitting at the root where any repo scan trips over it.
#   2. The allowed types are project-invented. No amount of good instinct
#      produces "deliver" or "repair" — the only way to satisfy this rule is to
#      have read it. A skill that merely writes idiomatic Conventional Commits
#      fails, so the assertion measures detection rather than taste.
cat > package.json <<'CFG'
{
  "name": "ledger-service",
  "version": "1.4.0",
  "type": "module",
  "private": true,
  "scripts": {
    "test": "node --test"
  },
  "commitlint": {
    "rules": {
      "type-enum": [2, "always", ["deliver", "repair", "tidy"]],
      "subject-case": [2, "always", "upper-case"],
      "header-max-length": [2, "always", 72],
      "scope-empty": [2, "always"]
    }
  }
}
CFG
git add -A
git commit -q -m "tidy: ADD PROJECT MANIFEST AND COMMIT RULES"
stage_feature
