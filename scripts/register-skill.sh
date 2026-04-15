#!/usr/bin/env bash
# register-skill.sh — Register a skill in agent discovery directories
#
# The skills CLI discovers skills from .agents/skills/ and .claude/skills/.
# Domain folders (universal/, frontend/, etc.) are for organization only.
# This script creates the required real directories and file symlinks.
#
# Usage:
#   ./scripts/register-skill.sh <skill-name>
#
# Example:
#   ./scripts/register-skill.sh tdd

set -euo pipefail

SKILL_NAME="${1:-}"

if [[ -z "$SKILL_NAME" ]]; then
  echo "Usage: $0 <skill-name>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Find the skill across all domain directories (non-hidden, non-scripts)
SKILL_SOURCE=""
DOMAIN=""
for domain_dir in "$REPO_ROOT"/*/; do
  domain_name="$(basename "$domain_dir")"
  candidate="$domain_dir$SKILL_NAME"
  if [[ -d "$candidate" && -f "$candidate/SKILL.md" ]]; then
    SKILL_SOURCE="$candidate"
    DOMAIN="$domain_name"
    break
  fi
done

if [[ -z "$SKILL_SOURCE" ]]; then
  echo "Error: No skill named '$SKILL_NAME' found." >&2
  echo "Create the skill directory and SKILL.md first, then run this script." >&2
  exit 1
fi

echo "Found: $DOMAIN/$SKILL_NAME"
echo ""

AGENT_DIRS=(".agents/skills" ".claude/skills")
REGISTERED=0

for agent_dir in "${AGENT_DIRS[@]}"; do
  target="$REPO_ROOT/$agent_dir/$SKILL_NAME"

  if [[ -d "$target" ]]; then
    echo "  $agent_dir/$SKILL_NAME already exists — skipping"
    continue
  fi

  mkdir -p "$target"

  while IFS= read -r file; do
    filename="$(basename "$file")"
    ln -s "../../../$DOMAIN/$SKILL_NAME/$filename" "$target/$filename"
    echo "  $agent_dir/$SKILL_NAME/$filename -> $DOMAIN/$SKILL_NAME/$filename"
  done < <(find "$SKILL_SOURCE" -maxdepth 1 -type f | sort)

  REGISTERED=$((REGISTERED + 1))
done

echo ""
if [[ $REGISTERED -gt 0 ]]; then
  echo "Registered '$SKILL_NAME' in ${REGISTERED} agent director$([ $REGISTERED -eq 1 ] && echo y || echo ies)."
  echo ""
  echo "Next steps:"
  echo "  1. Add '$SKILL_NAME' to the Available Skills table in README.md"
  echo "  2. Commit the new symlinks: git add .agents/skills/$SKILL_NAME .claude/skills/$SKILL_NAME"
else
  echo "Nothing to do — '$SKILL_NAME' is already registered everywhere."
fi
