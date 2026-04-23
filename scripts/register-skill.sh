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

  mkdir -p "$target"

  ADDED=0
  # Symlink every top-level entry (files AND directories). Subdirectories are
  # linked as whole dirs so their contents (e.g. references/*.md) come along.
  # Idempotent: skips entries that already exist.
  while IFS= read -r entry; do
    name="$(basename "$entry")"
    link="$target/$name"
    if [[ -L "$link" || -e "$link" ]]; then
      continue
    fi
    ln -s "../../../$DOMAIN/$SKILL_NAME/$name" "$link"
    echo "  $agent_dir/$SKILL_NAME/$name -> $DOMAIN/$SKILL_NAME/$name"
    ADDED=$((ADDED + 1))
  done < <(find "$SKILL_SOURCE" -mindepth 1 -maxdepth 1 \( -type f -o -type d \) | sort)

  if [[ $ADDED -gt 0 ]]; then
    REGISTERED=$((REGISTERED + 1))
  else
    echo "  $agent_dir/$SKILL_NAME already up to date"
  fi
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
