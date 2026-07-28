source "$FIXTURE_DIR/../../lib.sh"
init_repo
cat > commitlint.config.js <<'CFG'
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'subject-case': [2, 'always', 'lower-case'],
    'subject-full-stop': [2, 'never', '.'],
  },
};
CFG
mkdir -p .husky
cat > .husky/commit-msg <<'HOOK'
#!/usr/bin/env sh
npx --no-install commitlint --edit "$1"
HOOK
chmod +x .husky/commit-msg
git add -A
git commit -q -m "chore: Add commitlint config"
stage_feature
