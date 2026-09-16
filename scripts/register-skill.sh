#!/usr/bin/env bash
# register-skill.sh — Register a skill in agent discovery directories
#
# Agents (Claude Code, Cursor, Roo) discover skills from .agents/skills/ and
# .claude/skills/. Domain folders (universal/, frontend/, etc.) hold the real
# files. This script creates the discovery directories and file symlinks.
#
# The discovery directories are gitignored, not committed: a symlink and its
# target are two paths to one skill, and the `skills` CLI picks the symlink,
# hashes nothing (empty-string digest) and then refuses to update because
# "multiple current paths match". Consumers install from the domain folders.
#
# Usage:
#   ./scripts/register-skill.sh <skill-name>
#   ./scripts/register-skill.sh --all      # regenerate everything (after a clone)
#
# Example:
#   ./scripts/register-skill.sh tdd

set -euo pipefail

SKILL_NAME="${1:-}"

if [[ -z "$SKILL_NAME" ]]; then
  echo "Usage: $0 <skill-name> | --all" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --all: register every skill found in every domain folder. This is the
# after-clone bootstrap, since the discovery directories are not committed.
if [[ "$SKILL_NAME" == "--all" ]]; then
  found=0
  while IFS= read -r skill_md; do
    found=$((found + 1))
    bash "${BASH_SOURCE[0]}" "$(basename "$(dirname "$skill_md")")"
  done < <(cd "$REPO_ROOT" && find . -mindepth 3 -maxdepth 3 -name SKILL.md -not -path "./.*" | sort)
  if [[ $found -eq 0 ]]; then
    echo "No skills found in any domain folder." >&2
    exit 1
  fi
  exit 0
fi

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

  CHANGED=0

  # Prune dangling symlinks (source file/dir was renamed or moved). Only
  # removes broken symlinks — never real files or live links.
  for link in "$target"/* "$target"/.*; do
    [[ -e "$link" || -L "$link" ]] || continue
    base="$(basename "$link")"
    [[ "$base" == "." || "$base" == ".." ]] && continue
    if [[ -L "$link" && ! -e "$link" ]]; then
      rm "$link"
      echo "  pruned $agent_dir/$SKILL_NAME/$base (dangling)"
      CHANGED=$((CHANGED + 1))
    fi
  done

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
    CHANGED=$((CHANGED + 1))
  done < <(find "$SKILL_SOURCE" -mindepth 1 -maxdepth 1 \( -type f -o -type d \) | sort)

  if [[ $CHANGED -gt 0 ]]; then
    REGISTERED=$((REGISTERED + 1))
  else
    echo "  $agent_dir/$SKILL_NAME already up to date"
  fi
done

echo ""
if [[ $REGISTERED -gt 0 ]]; then
  echo "Registered '$SKILL_NAME' in ${REGISTERED} agent director$([ $REGISTERED -eq 1 ] && echo y || echo ies)."
  echo ""
  echo "Next step: add '$SKILL_NAME' to the Available Skills table in README.md."
  echo "The symlinks themselves are gitignored — nothing to commit here."
else
  echo "Nothing to do — '$SKILL_NAME' is already registered everywhere."
fi
