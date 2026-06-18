#!/usr/bin/env bash
# 把 Series Studio 框架合併安裝進 ~/.claude/（不覆蓋你其他 agents/skills）
set -e
SRC="$(cd "$(dirname "$0")" && pwd)/claude"
DEST="${HOME}/.claude"
mkdir -p "$DEST/agents" "$DEST/skills" "$DEST/series-studio"
rsync -a "$SRC/agents/" "$DEST/agents/"
rsync -a "$SRC/skills/" "$DEST/skills/"
rsync -a "$SRC/series-studio/" "$DEST/series-studio/"
echo "✅ 已安裝到 $DEST"
echo "下一步：把 MINIMAX_API_KEY 放到 ~/.claude/series-studio/.env"
