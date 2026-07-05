# Series Studio

設定驅動的 **YouTube 影片系列工廠**——一個「系列」= 一個資料夾，放固定設定檔，由一組專職 Claude Code subagent 與 skill 自動產出每一集（腳本 → 配音 → 動畫 → 實機 demo → BGM → 組裝 → SEO → 上架），並維護跨集 context。

從 [hello-agents-video](https://github.com/odafeng/hello-agents-video) 的實戰製作抽象而來。

## 結構（鏡像 `~/.claude/`）
```
claude/
  agents/vid-*.md            # 7 個專職 subagent：編劇/事實查核/配音/動畫/美術/音樂/SEO
  agents/colon-and-code.md   # 系列主理人：Colon & Code（頻道 DNA / 安全鐵則 / QC gate / SEO）
  agents/ai-storyteller.md   # 系列主理人：《AI 說書人》
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

> ⚠️ **活檔（`~/.claude/`）是唯一真相**；CONVENTIONS / agents / skills / template 有改就要
> commit 回本 repo（規則見 CONVENTIONS.md「完工回灌」）。金鑰一律不進 repo。

## 安裝
```bash
./install.sh            # 把 claude/* 合併進 ~/.claude/（不覆蓋你其他 agents/skills）
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
