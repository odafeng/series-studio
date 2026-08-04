#!/usr/bin/env bash
# 建立本系列自己的斷句 QC 環境。
# ⚠️ 不要 symlink 到別的系列資料夾——那個系列一搬走或刪掉，這裡就整個斷。
set -euo pipefail
cd "$(dirname "$0")"
if [ -e .venv-phrasing ]; then
  echo "voiceover/.venv-phrasing 已存在，先移除再跑（symlink 也算）"; exit 1
fi
python3 -m venv .venv-phrasing
./.venv-phrasing/bin/python -m pip install -q --upgrade pip
./.venv-phrasing/bin/python -m pip install -q -r requirements-phrasing.txt
echo "✓ 完成。首次執行會下載 whisper small 與 forced-align model。"
echo "  Release gate：voiceover/.venv-phrasing/bin/python voiceover/forced_align_phrasing.py --ep N"
