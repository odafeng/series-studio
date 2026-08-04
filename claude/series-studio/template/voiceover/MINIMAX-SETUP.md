# MiniMax 旁白設定

Claude 在系列根目錄工作時，以 `series.yaml voice` 為唯一真相，不把 model、voice ID 或替換詞寫死在 agent prompt。

## 設定

```yaml
voice:
  provider: minimax
  model: speech-2.8-hd
  voice_id: "YOUR_CLONED_VOICE_ID"
  speed: 1.15
  vol: 1.0
  pitch: 0
  emotion: happy
  tts_replacements:
    "DeepSeek-R1-Zero": "Deep Seek, R One, Zero"
    "現在進 RL 的核心": "現在進 R L 的核心"
```

Endpoint：`POST https://api.minimax.io/v1/t2a_v2`。API key 放在 gitignored `.env` 或 `~/.claude/series-studio/.env`：

```text
MINIMAX_API_KEY=...
MINIMAX_GROUP_ID=...
```

`tts_replacements` 只改送進 MiniMax 的 audio text，不改 script、manifest caption 或字幕。英文術語需要拼讀時用這裡，不要污染觀眾看到的文字。

## Builder 與 cache

```bash
python3 tools/build_voice.py --ep N
python3 tools/build_voice.py --ep N --model speech-2.8-hd  # 一次性 A/B
```

cache hash 必須包含 model、voice/audio settings、實際 audio text、詞庫命中與 replacement 結果。舊 manifest 沒有 `model` 欄位時視為 legacy `speech-02-hd`；不要拿舊 cache 冒充 2.8。

## Release gate

```bash
voiceover/.venv-phrasing/bin/python voiceover/forced_align_phrasing.py --ep N
voiceover/.venv-phrasing/bin/python voiceover/forced_align_phrasing.py \
  --ep N --cue-start 0 --cue-end 99
```

- exit 0：乾淨
- exit 1：找到詞內斷句缺陷
- exit 2：對齊失敗；QC 不完整，不可當 PASS

修正順序：fresh take → best-of-N（保留現有最佳）→ 重抽十次以上仍系統性失敗才做 surgical silence removal。任一 audio 改動後重跑 builder 與 forced-align；旁白、英文術語、manifest hash/audio 與使用者純音檔實聽全部鎖定後，才產字幕與開始 render。

`pronunciation_dict` 對既有 clone voice 曾以 A/B 證實無效；不要假設詞庫一定生效。讀音錯優先改寫或重抽，所有判斷以實際 audio 為準。
