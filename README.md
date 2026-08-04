# Series Studio

[![CI](https://github.com/odafeng/series-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/odafeng/series-studio/actions/workflows/ci.yml)
[![Claude Code](https://img.shields.io/badge/Claude_Code-agentic_workflow-D97757)](https://docs.anthropic.com/en/docs/claude-code)
[![Remotion](https://img.shields.io/badge/video-Remotion-7652F4)](https://www.remotion.dev/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**A production system for episodic video—not a one-shot video generator.**

設定驅動的 **YouTube 影片系列工廠**：一個「系列」就是一份長期維護的 production context，由專職 Claude Code subagents 與 skills 完成腳本 → 事實查核 → 配音 → Remotion 動畫 → demo → BGM → SEO → 安全上架，並把每一集學到的規則留給下一集。

```text
series.yaml + sources + series-context.md
                    │
                    ▼
 script ──▶ fact-check ──▶ voice ──▶ Remotion ──▶ QA gates ──▶ unlisted upload
    ▲                                                        │
    └──────────── cross-episode memory ◀──────────────────────┘
```

從 [hello-agents-video](https://github.com/odafeng/hello-agents-video) 的實戰製作抽象而來。

## 結構（鏡像 `~/.claude/`）
```
claude/
  agents/vid-*.md            # 7 個專職 subagent：編劇/事實查核/配音/動畫/美術/音樂/SEO
  agents/colon-and-code.md   # opinionated real-world example：技術頻道主理人
  agents/ai-storyteller.md   # opinionated real-world example：說書頻道主理人
  skills/new-series/         # 建系列骨架
  skills/produce-episode/    # 一集 orchestrator（含三道審核關，回寫 context）
  skills/auto-produce-next/  # 排程自動製作下一集（無人工關 → unlisted，絕不 public）
  series-studio/
    CONVENTIONS.md           # 通用技術 playbook
    template/                # 系列模板（series.yaml / voice-style / source / brand /
                             #   series-context / voiceover(tw_lexicon) / remotion 元件 /
                             #   tools：build_voice / generate_bgm / build_script_editor /
                             #         build_subtitle_cues / build_recording_script）
    youtube/                 # 共用上傳工具 upload.py（OAuth 憑證不進 repo，見 youtube/README）
```

> [!IMPORTANT]
> API keys、OAuth credentials、YouTube token 與 voice IDs 一律留在本機 `.env`／credential files，
> 不可放進系列資料夾或 commit 到 repo。

## 安裝
```bash
./install.sh --dry-run  # 先預覽
./install.sh            # 合併進 ~/.claude/；同名檔預設保留
# ./install.sh --force  # 明確要求時才覆寫 Series Studio 的同名檔案
# 把 MINIMAX_API_KEY 放到 ~/.claude/series-studio/.env（全系列共用）
```

## 用法
```bash
# 1) 開新系列
/new-series                       # 長出系列資料夾骨架
# 2) 填 series.yaml / voice-style.md / 把素材放 source/（或設 github repo）
# 3) cd 進系列資料夾，逐集製作
/produce-episode 1
```

## 需求
- Claude Code
- Node + Remotion（`remotion/` 內 `npm install`）、ffmpeg
- MiniMax 克隆聲（voice_id + API key）
- YouTube 上傳：Google OAuth（見 `CONVENTIONS.md` 上架段）
- macOS（實機螢幕錄影用 avfoundation；其他平台需調整）

## 設計理念
拆細、可並行、有審核關；技術細節單一真實來源（`CONVENTIONS.md` + 各系列 `series.yaml`/`voice-style.md`）；詞庫與 `series-context.md` 跨集累積、愈做愈順。

## 三道 publishing safety gates

1. **Script gate**：來源、授權署名與口語稿人工確認。
2. **Media gate**：旁白、字幕、畫面與 demo 數字一致。
3. **Publish gate**：自動流程只允許上傳為 `unlisted`；改成 `public` 必須人工操作。

## 測試

```bash
bash -n install.sh
bash tests/test_install.sh
python3 -m pytest -q
```

## License

MIT — see [LICENSE](LICENSE). 你放進新系列的原始素材仍各自受其原授權約束。
