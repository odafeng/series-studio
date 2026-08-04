#!/usr/bin/env bash
# Safely merge Series Studio into a Claude Code configuration directory.
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)/claude"
TARGET_DIR="${CLAUDE_HOME:-${HOME}/.claude}"
DRY_RUN=false
FORCE=false

usage() {
  printf 'Usage: %s [--dry-run] [--force]\n' "$0"
  printf '  --dry-run  Show source files without changing the destination.\n'
  printf '  --force    Replace same-name Series Studio files in the destination.\n'
}

while (($#)); do
  case "$1" in
    --dry-run) DRY_RUN=true ;;
    --force) FORCE=true ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if ! command -v rsync >/dev/null 2>&1; then
  printf 'rsync is required but was not found on PATH.\n' >&2
  exit 1
fi

if [[ "$DRY_RUN" == true ]]; then
  printf 'Dry run: files available for installation into %s\n' "$TARGET_DIR"
  find "$SOURCE_DIR" -type f -print | sed "s#^$SOURCE_DIR/##" | sort
  exit 0
fi

mkdir -p "$TARGET_DIR/agents" "$TARGET_DIR/skills" "$TARGET_DIR/series-studio"

RSYNC_ARGS=(-a)
if [[ "$FORCE" != true ]]; then
  RSYNC_ARGS+=(--ignore-existing)
fi

rsync "${RSYNC_ARGS[@]}" "$SOURCE_DIR/agents/" "$TARGET_DIR/agents/"
rsync "${RSYNC_ARGS[@]}" "$SOURCE_DIR/skills/" "$TARGET_DIR/skills/"
rsync "${RSYNC_ARGS[@]}" "$SOURCE_DIR/series-studio/" "$TARGET_DIR/series-studio/"

printf 'Installed Series Studio into %s\n' "$TARGET_DIR"
if [[ "$FORCE" != true ]]; then
  printf 'Existing same-name files were preserved. Use --force to replace them.\n'
fi
printf 'Next: store MINIMAX_API_KEY in %s/series-studio/.env\n' "$TARGET_DIR"
