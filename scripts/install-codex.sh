#!/usr/bin/env bash
# Install Apex for OpenAI Codex CLI in prompt-only mode.
#
# Codex reads skills from .agents/skills (per repo) or ~/.agents/skills (global).
# Claude Code hooks/subagents don't exist there, so the guardrails are NOT enforced:
# the skills still drive the same workflow and the apex.py CLI still lints output.
#
# Usage:  scripts/install-codex.sh [target-dir]    (default: ./.agents)
#         scripts/install-codex.sh ~/.agents        (global install)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-.agents}"
mkdir -p "$DEST/skills"
DEST="$(cd "$DEST" && pwd)"
HOME_DIR="$DEST/apex"

rm -rf "$HOME_DIR"
mkdir -p "$HOME_DIR"
cp -R "$SRC/scripts" "$SRC/skills" "$SRC/agents" "$HOME_DIR/"
find "$HOME_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} +

for dir in "$SRC"/skills/*/; do
  name="$(basename "$dir")"
  out="$DEST/skills/apex-$name"
  rm -rf "$out"
  cp -R "$dir" "$out"
  # Point plugin paths at the installed copy, rename skills, and use Codex's $skill syntax.
  sed -e "s|\${CLAUDE_PLUGIN_ROOT}|$HOME_DIR|g" \
      -e "s|^name: $name\$|name: apex-$name|" \
      -e "s|/apex:\([a-z-]*\)|\$apex-\1|g" \
      "$dir/SKILL.md" > "$out/SKILL.md"
  if [ -d "$dir/references" ]; then
    rm -rf "$out/references"
  fi
done

echo "Apex installed for Codex at $DEST (prompt-only mode)."
echo "Skills: \$apex-init, \$apex-audit, \$apex-run-session, \$apex-status, \$apex-defer, \$apex-doctor"
echo "Note: Claude Code's hook guardrails don't run in Codex; see docs/codex.md."
