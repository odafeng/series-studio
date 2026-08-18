#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

TARGET="$TEST_ROOT/claude-home"
mkdir -p "$TARGET/agents"
printf 'keep-me\n' > "$TARGET/agents/vid-voice.md"

CLAUDE_HOME="$TARGET" "$REPO_ROOT/install.sh" >/dev/null
grep -qx 'keep-me' "$TARGET/agents/vid-voice.md"
test -f "$TARGET/skills/new-series/SKILL.md"
test -f "$TARGET/series-studio/template/series.yaml"

CLAUDE_HOME="$TARGET" "$REPO_ROOT/install.sh" --force >/dev/null
cmp "$REPO_ROOT/claude/agents/vid-voice.md" "$TARGET/agents/vid-voice.md"

DRY_TARGET="$TEST_ROOT/dry-target"
OUTPUT="$(CLAUDE_HOME="$DRY_TARGET" "$REPO_ROOT/install.sh" --dry-run)"
test ! -e "$DRY_TARGET"
grep -q 'agents/vid-voice.md' <<< "$OUTPUT"

if CLAUDE_HOME="$TARGET" "$REPO_ROOT/install.sh" --unknown >/dev/null 2>&1; then
  printf 'unknown option unexpectedly succeeded\n' >&2
  exit 1
fi
