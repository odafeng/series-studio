#!/usr/bin/env python3
"""腳本 lint — 交稿前自動掃過，取代「編劇要記得自己掃」。

規則的單一真相是 `voice-style.md`：破音字對照表直接從那份文件解析，
所以改文件就等於改規則，兩邊不會漂移。句構規則（破折號、28 字斷點…）
邏輯性太強，寫在本檔。

用法：
    python3 tools/lint_script.py --ep 1
    python3 tools/lint_script.py --selftest

exit 0 = 沒有 ERROR（WARN 不擋）；exit 1 = 有 ERROR。
"""
import argparse
import re
import sys
from pathlib import Path

PUNCT = "，。？！；：、「」『』（）"
MAX_RUN = 28  # 一句話裡沒有標點的最長字數

# 只掃【旁白】。這些是「唸出來會出事」的規則，畫面/字幕不唸，不受限。
FORBIDDEN = {
    "實作召喚": ["跑跑看", "打開終端機", "clone 下來", "照著做", "跟著做一遍", "動手做做看"],
    "出題": ["留言區", "留一題", "歡迎討論", "你覺得呢", "留言告訴我"],
    "導讀腔": ["作者說", "作者主張", "作者認為", "書裡寫", "原書第", "本書第", "這本書提到"],
}


def parse_narration(md: str):
    """回傳 [(行號, 旁白文字)]。行號是該段旁白第一行在檔案裡的位置（1-indexed）。"""
    out, lines, i, n = [], md.split("\n"), 0, len(md.split("\n"))
    while i < n:
        if lines[i].startswith("**【旁白】**"):
            start, buf = i + 2, []
            i += 1
            while i < n:
                s = lines[i].strip()
                if s == "---" or lines[i].startswith("## ") or lines[i].startswith("**【"):
                    break
                buf.append(lines[i])
                i += 1
            text = "\n".join(buf).strip()
            if text:
                out.append((start, text))
            continue
        i += 1
    return out


def load_homophone_table(voice_style: Path):
    """從 voice-style.md 的『別寫 | 改寫成 | 原因』表格解析禁用詞。"""
    if not voice_style.exists():
        raise SystemExit(f"找不到 {voice_style}——破音字規則的真相在那份文件裡。")
    rows = re.findall(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$',
                      voice_style.read_text(encoding="utf-8"), re.M)
    table = {}
    for bad, good, why in rows:
        if bad in ("別寫", "---") or set(bad) <= set("- "):
            continue
        for term in re.split(r'[、／/]', bad):
            term = term.strip()
            if term:
                table[term] = (good.strip(), why.strip())
    if not table:
        raise SystemExit(
            "voice-style.md 裡找不到破音字對照表。"
            "表格格式若改過，請同步更新 lint_script.py 的解析。")
    return table


def lint(narration, homophones):
    """回傳 (errors, warns, ear_check)。"""
    errors, warns, ear = [], [], set()
    for lineno, text in narration:
        flat = re.sub(r'\s', '', text)

        for term, (good, why) in homophones.items():
            if term in flat:
                errors.append((lineno, "破音字", f"「{term}」→ 改成「{good}」（{why}）"))

        for rule, terms in FORBIDDEN.items():
            for t in terms:
                if t in flat:
                    errors.append((lineno, rule, f"旁白出現「{t}」"))

        if "——" in flat or "—" in flat:
            errors.append((lineno, "破折號", "MiniMax 對破折號停頓長度不穩，改成句號或冒號"))

        # 沒有標點的最長連續區段
        for run in re.split(f"[{PUNCT}]", flat):
            if len(run) > MAX_RUN:
                warns.append((lineno, "長串無標點",
                              f"{len(run)} 字沒有換氣點：「{run[:18]}…」"))

        for m in re.finditer(r'\d+\.\d+', flat):
            warns.append((lineno, "小數點", f"「{m.group()}」建議移到【畫面】，旁白改口語說法"))

        # 英文詞／人名只能靠耳朵，蒐集成清單給配音師
        for m in re.finditer(r'[A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z][A-Za-z0-9]*)*', text):
            w = m.group().strip()
            if len(w) >= 2 and not w.isdigit():
                ear.add(w)
    return errors, warns, sorted(ear, key=str.lower)


def report(errors, warns, ear, narration, name):
    for lineno, rule, msg in sorted(errors):
        print(f"{name}:{lineno}: ERROR [{rule}] {msg}")
    for lineno, rule, msg in sorted(warns):
        print(f"{name}:{lineno}: warn  [{rule}] {msg}")
    words = sum(len(re.sub(r'\s', '', t)) for _, t in narration)
    print(f"\n旁白 {words} 字 / {len(narration)} 段"
          f"｜ERROR {len(errors)}｜warn {len(warns)}")
    if ear:
        print(f"\n耳朵確認清單（含英文，verify_phrasing 對這些句子不可信）：\n  {'、'.join(ear)}")
    return 1 if errors else 0


def selftest():
    """已知有雷的樣本必須被抓到；改壞規則時這裡會先紅。"""
    sample = """## 01 測試

**【畫面】** 這裡寫 重跑一次 不該被抓，因為畫面不唸。

**【旁白】**
一步走錯不是重跑一次就好。我們來跑跑看，順便留言區聊聊。作者說這樣不行——真的不行。
"""
    homophones = {"重跑一次": ("賠的就是…", "重 chóng")}
    errors, *_ = lint(parse_narration(sample), homophones)
    rules = {r for _, r, _ in errors}
    expected = {"破音字", "實作召喚", "出題", "導讀腔", "破折號"}
    missing = expected - rules
    assert not missing, f"漏抓：{missing}"
    assert not any("重跑一次" in m for _, r, m in errors if r != "破音字"), "畫面指示被誤掃"
    assert len(errors) == 5, f"預期 5 個 ERROR，實得 {len(errors)}：{errors}"
    print("✓ selftest 通過：5 條規則都抓得到，且不誤掃【畫面】")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, help="集數 N")
    ap.add_argument("--selftest", action="store_true", help="跑內建測試")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.ep is None:
        ap.error("要嘛給 --ep N，要嘛給 --selftest")
    epnn = f"{args.ep:02d}"
    md_path = Path(f"episodes/ep{epnn}/script/ep{epnn}-script.md")
    if not md_path.exists():
        raise SystemExit(f"找不到腳本：{md_path}")
    narration = parse_narration(md_path.read_text(encoding="utf-8"))
    homophones = load_homophone_table(Path("voice-style.md"))
    errors, warns, ear = lint(narration, homophones)
    return report(errors, warns, ear, narration, md_path.name)


if __name__ == "__main__":
    sys.exit(main())
