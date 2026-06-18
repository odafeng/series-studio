# 一個「系列」資料夾

把這些固定檔放好，用 `/produce-episode N` 就能產出第 N 集。

- `series.yaml` — 系列設定（聲音、視覺、素材來源、授權…）
- `voice-style.md` — 主持人口吻
- `source/` — 素材（local：ep01.md…；或 series.yaml 設 github repo）
- `brand/` — 片頭影片 intro.mp4、縮圖元素
- `series-context.md` — 系列聖經（自動維護，跨集 context）
- `voiceover/tw_lexicon.json` — 破音字詞庫（已含基底，會累積）
- `remotion/` — 動畫專案（基礎元件已備，每集生成 scenesNN/EpisodeNN）
- `episodes/` — 產出（自動生成）
- `.env` — MINIMAX_API_KEY（或放 ~/.claude/series-studio/.env 全系列共用）

製作流程與規範見 `~/.claude/skills/produce-episode`。
