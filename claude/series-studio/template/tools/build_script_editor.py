#!/usr/bin/env python3
"""
build_script_editor.py — 腳本關通用工具（所有系列共用）

把 episodes/epNN/script/epNN-script.md 轉成「可編輯的腳本編輯器 HTML」，
用於 produce-episode 流程的「🚪 腳本關」：給使用者直接過目並編輯。
- 每段【旁白】都能直接改、輸入自己的話
- 可在任意位置插入自己的新段落、刪除段落
- 一鍵匯出 Markdown（epNN-script-edited.md）給製作流程接手
- 自動存 localStorage（重整不丟）、可還原原稿、可複製全部旁白
- 旁白字數／預估時長即時更新
- 配色自動套用 ./series.yaml 的 visual token（找不到就用暖光預設）

用法：python3 tools/build_script_editor.py --ep N
輸出：episodes/epNN/script/epNN-script-editor.html
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

DEFAULT_COLORS = {
    "primary": "#F59E0B", "accent": "#FBBF24", "teal": "#2DD4BF",
    "bg": "#16213E", "surface": "#1C2A4D", "code": "#0C1326",
    "text": "#FFF7ED", "muted": "#94A3B8", "line": "#334155",
}


def load_colors():
    c = dict(DEFAULT_COLORS)
    p = Path("series.yaml")
    if p.exists():
        txt = p.read_text(encoding="utf-8")
        keymap = {"primary": "primary", "accent": "accent", "teal": "teal",
                  "bg": "bg", "surface": "surface", "code_bg": "code", "text": "text"}
        for ykey, ckey in keymap.items():
            m = re.search(rf'^\s*{ykey}:\s*["\']?(#[0-9A-Fa-f]{{6}})', txt, re.M)
            if m:
                c[ckey] = m.group(1)
    return c


# 實測值（EP01，MiniMax 克隆聲 @ speed 1.15）：2525 字 / 422.9 秒 = 5.97 字/秒。
# 換算成 speed 1.0 的基準 ≈ 5.19 字/秒。舊常數 4.3 把 7.0 分的稿估成 9.8 分，
# 誤差 40%，害編劇照著寫出來的集數長度全部不對——所以這裡改用實測值 × 系列語速。
BASE_CPS = 5.19  # 字/秒 @ speed 1.0


def chars_per_min():
    speed = 1.0
    p = Path("series.yaml")
    if p.exists():
        m = re.search(r'^\s*speed:\s*([0-9.]+)', p.read_text(encoding="utf-8"), re.M)
        if m:
            speed = float(m.group(1))
    return BASE_CPS * speed * 60


def license_markers():
    """從 series.yaml 抓授權署名的關鍵字，當作「不准掉」的護欄依據。"""
    marks = []
    p = Path("series.yaml")
    if p.exists():
        txt = p.read_text(encoding="utf-8")
        for key in ("license", "source_url"):
            m = re.search(rf'^\s*{key}:\s*["\']?([^"\'\n]+)', txt, re.M)
            if m:
                v = m.group(1).strip()
                marks.append(v.replace("https://", "").replace("http://", ""))
        m = re.search(r'^\s*attribution:\s*["\']?([^"\'\n]+)', txt, re.M)
        if m:
            # 取作者姓名那一段當指紋（整串太長、易因排版換行而誤判）
            a = re.search(r'改編自\s*([^（(]+)', m.group(1))
            if a:
                marks.append(a.group(1).strip())
    return [x for x in marks if x]


def _tail_credit(data):
    """片尾場景所有【畫面】指示串起來——授權 credit 就該長在這裡。

    只掃「整份 md 有沒有這些字」是無效護欄：作者名／Apache-2.0 在標頭註解和
    開場旁白裡也會出現，片尾 credit 整段被吃掉時照樣「找得到」。
    """
    scenes = [d for d in data if d["type"] == "scene"]
    if not scenes:
        return ""
    return "\n".join(b.get("screen", "") for b in scenes[-1].get("blocks", []))


def assert_license_survives(md):
    """片尾授權署名必須存在，且要能撐過 parse→匯出。

    Apache-2.0 要求保留署名。這段藏在【畫面】續行裡，掉了畫面上不會少一塊、
    人眼看不出來，所以每次 build 都硬檢查一次。
    """
    marks = license_markers()
    if not marks:
        return []
    tail = _tail_credit(parse_script(md))
    missing = [m for m in marks if m not in tail]
    if missing:
        return [f"🛑 片尾【畫面】的授權 credit 缺少：{'、'.join(missing)}"
                "（Apache-2.0 要求保留署名，請補回最後一個場景的 credit）"]
    tail_rt = _tail_credit(parse_script(build_md(parse_script(md))))
    lost = [m for m in marks if m not in tail_rt]
    if lost:
        return [f"🛑 授權署名撐不過 parse→匯出，會被靜悄悄吃掉：{'、'.join(lost)}"]
    return []


def _content_lines(md):
    """留下真正的內容行——空行與結構用的 `---` 由 build_md 自己補回，不算內容。"""
    return [s for s in (l.strip() for l in md.split("\n")) if s and s != "---"]


def assert_roundtrip_lossless(md):
    """**任何**內容都必須撐得過 parse → 匯出，不只授權署名。

    作者按「匯出 Markdown」拿到的就是 build_md 的結果，會拿去覆蓋原稿。
    所以「parse 不認得的東西」＝「作者一按匯出就永久消失的東西」，而且畫面上
    看不出來——這正是 assert_license_survives 當初要擋的那件事，只是那支
    只盯著授權那幾行。EP07 這一輪踩到兩個它盯不到的：
      ① 製作註記 374 行（整段沒有任何【畫面】/【旁白】標記）→ 只剩標題
      ② 7 個【畫面】區塊（連續卡、中間刻意沒有旁白）→ 後一張覆蓋前一張
    與其每踩一次補一個單點檢查，不如讓「內容不得減少」變成 build 的前提。
    """
    before = _content_lines(md)
    after = _content_lines(build_md(parse_script(md)))
    if before == after:
        return []
    missing = [l for l in before if l not in after]
    if missing:
        sample = "、".join(x[:26] for x in missing[:3])
        return [f"🛑 有 {len(missing)} 行內容撐不過 parse→匯出，作者一按「匯出 Markdown」"
                f"就會靜悄悄消失：{sample}…"]
    if len(before) != len(after):
        return [f"🛑 內容行數 parse 前 {len(before)}、匯出後 {len(after)}，有東西被複製或吃掉"]
    return ["🛑 內容順序在 parse→匯出後改變了"
            "（場景中段的散文目前的資料格式表達不了，請把它移到場景開頭）"]


def parse_script(md):
    """把腳本 md 解析成 [{type, ...}]。type: head/scene/marker/license。
    scene 另有 `prose`：該段裡不屬於任何【畫面】/【旁白】的文字（製作註記就是）。"""
    lines = md.split("\n")
    n = len(lines)
    i = 0
    data = []
    # head：第一個單井號標題 + 後續引言（> 行）
    while i < n:
        if lines[i].startswith("# ") and not lines[i].startswith("## "):
            head = [lines[i]]
            i += 1
            while (i < n and not lines[i].startswith("## ")
                   and lines[i].strip() != "---"
                   and not lines[i].strip().startswith("〔")):
                head.append(lines[i])
                i += 1
            data.append({"type": "head", "text": "\n".join(head).strip()})
            break
        if lines[i].startswith("## ") or lines[i].strip().startswith("〔"):
            break
        i += 1

    cur = None
    blk = None
    prose = []

    def new_block():
        return {"screen": "", "subtitle": "", "narration": ""}

    def close_block():
        """把當前 block 收進場景（空 block 不收）。"""
        nonlocal blk
        if cur is not None and blk and (blk["screen"] or blk["subtitle"] or blk["narration"]):
            cur["blocks"].append(blk)
        blk = None

    def flush():
        nonlocal cur, blk, prose
        if cur:
            close_block()
            # 尾端的空行與結構用的 --- 由 build_md 補回，不算內容。
            while prose and (not prose[-1].strip() or prose[-1].strip() == "---"):
                prose.pop()
            cur["prose"] = "\n".join(prose).strip("\n")
            data.append(cur)
            cur = None
        blk = None
        prose = []

    while i < n:
        line = lines[i]
        s = line.strip()
        if line.startswith("## "):
            flush()
            cur = {"type": "scene", "title": line.rstrip(), "prose": "", "blocks": []}
            i += 1
            continue
        if s.startswith("〔") and s.endswith("〕"):
            flush()
            t = "license" if ("授權" in s or "署名" in s) else "marker"
            data.append({"type": t, "text": s})
            i += 1
            continue
        if cur is not None:
            # 一個場景可以有多組「畫面→旁白」交錯（既有系列慣例）。
            # 每收完一段旁白就算一組結束，下一個標記開新的一組。
            m = re.match(r'\*\*【(畫面|字幕|旁白)】\*\*', line)
            if m:
                key = {"畫面": "screen", "字幕": "subtitle", "旁白": "narration"}[m.group(1)]
                # ⚠️ `blk[key]` 這個條件不可拿掉：同一種標記連續出現時（例如連著兩張
                # 【畫面】卡、中間刻意沒有旁白），少了它第二張會直接覆蓋第一張，
                # 匯出時靜悄悄少一張卡。EP07 因此掉了 7 個【畫面】區塊。
                if blk is None or blk["narration"] or blk[key]:
                    close_block()
                    blk = new_block()
                # 三種標記都可能跨行：【畫面】常是「同行開頭 + 續行」（例如片尾
                # 兩列授權 credit），【旁白】則多是標記獨佔一行、內容全在續行。
                # ⚠️ 只取首行會靜悄悄吃掉續行——那裡放的是 Apache-2.0 要求的署名。
                first = re.sub(r'^\*\*【..】\*\*\s*', '', line).rstrip()
                i += 1
                rest = []
                while i < n:
                    l2 = lines[i]
                    s2 = l2.strip()
                    # 必須在下一個標記就停，否則會把後面的內容一起吞掉。
                    if (s2 == "---" or l2.startswith("## ")
                            or l2.startswith("**【")
                            or (s2.startswith("〔") and s2.endswith("〕"))):
                        break
                    rest.append(l2)
                    i += 1
                blk[key] = "\n".join(([first] if first else []) + rest).strip()
                continue
            # 標記以外的行也要留著。製作註記整段就是這種——它沒有任何
            # 【畫面】/【旁白】標記，舊版直接跳過，作者一按匯出就少了 374 行。
            prose.append(line)
            i += 1
            continue
        i += 1
    flush()
    return data


TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>__TITLE__ — 腳本編輯器</title>
<style>
  :root{__ROOTVARS__}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:"Noto Sans TC","PingFang TC",sans-serif;line-height:1.7}
  header{position:sticky;top:0;z-index:10;background:var(--bg);
    border-bottom:1px solid var(--line);padding:14px 22px;
    display:flex;align-items:center;gap:16px;flex-wrap:wrap}
  header h1{font-size:17px;margin:0;font-weight:900}
  .stat{font-size:13px;color:var(--muted)}
  .stat b{color:var(--teal);font-size:15px}
  .spacer{flex:1}
  button{font-family:inherit;cursor:pointer;border:none;border-radius:9px;
    padding:9px 16px;font-size:14px;font-weight:700;transition:transform .1s,filter .15s}
  button:hover{filter:brightness(1.1)}
  button:active{transform:translateY(1px)}
  .btn-primary{background:var(--primary);color:var(--bg)}
  .btn-ghost{background:var(--surface);color:var(--text);border:1px solid var(--line)}
  main{max-width:920px;margin:0 auto;padding:24px 18px 120px}
  .intro-note{background:var(--code);border:1px dashed var(--line);border-radius:12px;
    padding:14px 18px;color:var(--muted);font-size:14px;margin-bottom:20px}
  .scene{background:var(--surface);border:1px solid var(--line);border-radius:14px;
    padding:18px 20px;margin-bottom:18px}
  .scene-title{width:100%;background:transparent;border:none;color:var(--accent);
    font-size:19px;font-weight:900;font-family:inherit;padding:2px 0 10px;
    border-bottom:1px solid var(--line);margin-bottom:12px}
  .scene-title:focus{outline:none;color:var(--primary)}
  .field{margin:10px 0}
  .label{font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);
    font-weight:700;margin-bottom:5px;display:flex;align-items:center;gap:8px}
  .label .pill{background:var(--code);color:var(--teal);padding:1px 8px;border-radius:20px;font-size:10px}
  textarea{width:100%;background:#0f1830;border:1px solid var(--line);border-radius:9px;
    color:var(--text);font-family:inherit;font-size:15px;line-height:1.75;padding:11px 13px;
    resize:none;overflow:hidden}
  textarea:focus{outline:none;border-color:var(--primary)}
  textarea.narration{background:var(--code);font-size:16px;border-left:3px solid var(--primary)}
  textarea.aux{font-size:13.5px;color:var(--muted)}
  .scene-foot{display:flex;justify-content:space-between;align-items:center;margin-top:8px}
  .wc{font-size:12px;color:var(--muted)}
  .wc b{color:var(--accent)}
  .row-actions{display:flex;gap:8px}
  .mini{font-size:12px;padding:5px 10px;border-radius:7px;background:#0f1830;
    color:var(--muted);border:1px solid var(--line)}
  .marker{background:var(--code);border:1px dashed var(--primary);border-radius:12px;
    padding:12px 18px;color:var(--accent);font-size:13px;text-align:center;margin-bottom:18px}
  .insert-bar{text-align:center;margin:6px 0 18px}
  .insert-bar button{background:transparent;color:var(--teal);border:1px dashed var(--line);font-size:13px}
  .saved{font-size:12px;color:var(--teal);opacity:0;transition:opacity .3s}
  .saved.show{opacity:1}
</style>
</head>
<body>
<header>
  <h1>__TITLE__ <span style="color:var(--primary)">· 腳本編輯器</span></h1>
  <span class="stat">旁白 <b id="totalWords">0</b> 字 · 約 <b id="totalTime">0</b> 分</span>
  <span class="saved" id="saved">已自動儲存 ✓</span>
  <span class="spacer"></span>
  <button class="btn-ghost" onclick="copyNarration()">複製全部旁白</button>
  <button class="btn-ghost" onclick="resetAll()">還原原始稿</button>
  <button class="btn-primary" onclick="downloadMd()">⬇ 匯出 Markdown</button>
</header>
<main id="main"></main>
<script>
const ORIGINAL = __DATA__;
const KEY = "__EPKEY__";
const CPM = __CPM__;   // 字/分，實測值 × series.yaml 的 speed
let data = load();
function load(){ try{ const s=localStorage.getItem(KEY); if(s) return JSON.parse(s);}catch(e){} return JSON.parse(JSON.stringify(ORIGINAL)); }
function save(){ localStorage.setItem(KEY, JSON.stringify(data));
  const s=document.getElementById('saved'); s.classList.add('show');
  clearTimeout(window._st); window._st=setTimeout(()=>s.classList.remove('show'),1200); }
function wc(t){ return (t||"").replace(/\s/g,"").length; }
function sceneWc(item){ return (item.blocks||[]).reduce((a,b)=>a+wc(b.narration),0); }
function autosize(ta){ ta.style.height="auto"; ta.style.height=ta.scrollHeight+"px"; }
function render(){
  const main=document.getElementById('main'); main.innerHTML="";
  data.forEach((item,idx)=>{
    if(item.type==="head"){ const d=document.createElement('div'); d.className="intro-note"; d.textContent="檔案標頭（匯出時保留）"; main.appendChild(d); return; }
    if(item.type==="marker"||item.type==="license"){ const d=document.createElement('div'); d.className="marker"; d.textContent=item.text; main.appendChild(d); addInsertBar(main,idx); return; }
    // 只有散文、沒有任何【畫面】/【旁白】的段落＝製作註記。它是配音/動畫/SEO
    // 的開工依據，不是要唸的東西，所以不給編輯，但匯出時原樣帶回去。
    if(item.prose && !(item.blocks||[]).length){
      const d=document.createElement('div'); d.className="intro-note";
      d.textContent=item.title.replace(/^##\s*/,"")+"（匯出時原樣保留，不在這裡編輯）";
      main.appendChild(d); addInsertBar(main,idx); return; }
    const card=document.createElement('div'); card.className="scene";
    const t=document.createElement('input'); t.className="scene-title"; t.value=item.title;
    t.oninput=()=>{item.title=t.value; save();}; card.appendChild(t);
    if(item.prose){ const d=document.createElement('div'); d.className="intro-note";
      d.textContent="本段另有註記文字，匯出時原樣保留"; card.appendChild(d); }
    const blocks=item.blocks||[]; const nb=blocks.length;
    blocks.forEach((b,bi)=>{
      if(nb>1){ const bl=document.createElement('div');
        bl.style.cssText="font:600 11px/1.6 ui-monospace,monospace;opacity:.42;margin:16px 0 2px;letter-spacing:.08em";
        bl.textContent="── 段 "+(bi+1)+" / "+nb; card.appendChild(bl); }
      card.appendChild(field("畫面（不唸）","aux","screen",b,idx));
      card.appendChild(field("字幕（不唸）","aux","subtitle",b,idx));
      card.appendChild(field("旁白（要唸）","narration","narration",b,idx,true));
    });
    const foot=document.createElement('div'); foot.className="scene-foot";
    const w=document.createElement('span'); w.className="wc"; w.id="wc"+idx; w.innerHTML="旁白 <b>"+sceneWc(item)+"</b> 字";
    const ra=document.createElement('div'); ra.className="row-actions";
    const del=document.createElement('button'); del.className="mini"; del.textContent="刪除此段";
    del.onclick=()=>{ if(confirm("確定刪除「"+item.title+"」？")){ data.splice(idx,1); save(); render(); } };
    ra.appendChild(del); foot.appendChild(w); foot.appendChild(ra); card.appendChild(foot);
    main.appendChild(card); addInsertBar(main,idx);
  });
  updateTotals();
}
function field(label,cls,key,obj,idx,isNarration){
  const f=document.createElement('div'); f.className="field";
  const l=document.createElement('div'); l.className="label"; l.innerHTML=label+(isNarration?' <span class="pill">會唸出來</span>':'');
  const ta=document.createElement('textarea'); ta.className=cls; ta.value=obj[key]||"";
  ta.oninput=()=>{ obj[key]=ta.value; autosize(ta); if(isNarration){ document.getElementById('wc'+idx).innerHTML="旁白 <b>"+sceneWc(data[idx])+"</b> 字"; updateTotals(); } save(); };
  f.appendChild(l); f.appendChild(ta); requestAnimationFrame(()=>autosize(ta)); return f;
}
function addInsertBar(main,idx){
  const bar=document.createElement('div'); bar.className="insert-bar";
  const b=document.createElement('button'); b.textContent="＋ 在這裡插入我自己的段落";
  b.onclick=()=>{ data.splice(idx+1,0,{type:"scene",title:"## 新段落（我自己加的）",blocks:[{screen:"",subtitle:"",narration:"在這裡輸入你想講的話……"}]}); save(); render(); };
  bar.appendChild(b); main.appendChild(bar);
}
function updateTotals(){ let tot=0; data.forEach(i=>{ if(i.type==="scene") tot+=sceneWc(i); });
  document.getElementById('totalWords').textContent=tot;
  document.getElementById('totalTime').textContent=(tot/CPM).toFixed(1); }
function buildMd(){ let out=[];
  data.forEach(item=>{
    if(item.type==="head"){ out.push(item.text+"\n\n---"); }
    else if(item.type==="marker"){ out.push("\n"+item.text+"\n\n---"); }
    else if(item.type==="license"){ out.push("\n"+item.text); }
    else{ let s="\n"+item.title+"\n";
      if(item.prose) s+="\n"+item.prose+"\n";
      (item.blocks||[]).forEach(b=>{
        if(b.screen) s+="\n**【畫面】** "+b.screen+"\n";
        if(b.subtitle) s+="\n**【字幕】** "+b.subtitle+"\n";
        if(b.narration) s+="\n**【旁白】**\n"+b.narration+"\n";
      });
      s+="\n---"; out.push(s); }
  });
  return out.join("\n"); }
function downloadMd(){ const blob=new Blob([buildMd()],{type:"text/markdown;charset=utf-8"});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download="__DLNAME__"; a.click(); }
function copyNarration(){ const t=data.filter(i=>i.type==="scene").map(i=>i.title+"\n"+(i.blocks||[]).map(b=>b.narration).filter(Boolean).join("\n")).join("\n\n");
  navigator.clipboard.writeText(t).then(()=>alert("已複製全部旁白到剪貼簿")); }
function resetAll(){ if(confirm("還原成原始稿？你目前的修改會被清掉。")){ data=JSON.parse(JSON.stringify(ORIGINAL)); save(); render(); } }
render();
</script>
</body>
</html>
'''


def build_html(data, colors, title, epkey, dlname):
    rootvars = ";".join(f"--{k}:{v}" for k, v in [
        ("primary", colors["primary"]), ("accent", colors["accent"]), ("teal", colors["teal"]),
        ("bg", colors["bg"]), ("surface", colors["surface"]), ("code", colors["code"]),
        ("text", colors["text"]), ("muted", colors["muted"]), ("line", colors["line"]),
    ])
    html = TEMPLATE
    html = html.replace("__ROOTVARS__", rootvars)
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    html = html.replace("__EPKEY__", epkey)
    html = html.replace("__CPM__", f"{chars_per_min():.1f}")
    html = html.replace("__DLNAME__", dlname)
    html = html.replace("__TITLE__", title)
    return html


def build_md(data):
    """買 buildMd() 的 Python 分身，只給 selftest 用（正式匯出走瀏覽器那份 JS）。
    兩邊邏輯必須一致；改 JS 的 buildMd 時記得同步這裡，selftest 會抓到不一致。"""
    out = []
    for item in data:
        if item["type"] == "head":
            out.append(item["text"] + "\n\n---")
        elif item["type"] == "marker":
            out.append("\n" + item["text"] + "\n\n---")
        elif item["type"] == "license":
            out.append("\n" + item["text"])
        else:
            s = "\n" + item["title"] + "\n"
            if item.get("prose"):
                s += "\n" + item["prose"] + "\n"
            for b in item["blocks"]:
                if b["screen"]:
                    s += "\n**【畫面】** " + b["screen"] + "\n"
                if b["subtitle"]:
                    s += "\n**【字幕】** " + b["subtitle"] + "\n"
                if b["narration"]:
                    s += "\n**【旁白】**\n" + b["narration"] + "\n"
            s += "\n---"
            out.append(s)
    return "\n".join(out)


SELFTEST_MD = """# EP99 — 測試

---

## 01 多組交錯

**【畫面】** 第一個畫面。

**【旁白】**
第一段旁白。

**【畫面】** 第二個畫面，這行後面還有續行：
`續行一：這是 Apache-2.0 要求的署名`
`續行二：不能被吃掉`

**【字幕】** 一行字幕

**【旁白】**
第二段旁白。

---

## 02 連續兩張畫面卡

**【畫面】** 第一張卡：這張刻意沒有配對旁白。

**【畫面】** 第二張卡：舊版會讓這張把上面那張蓋掉。

**【旁白】**
兩張卡講完才有這段旁白。

---

## 製作註記（不進畫面、不唸）

這一段沒有任何【畫面】或【旁白】標記，整段都是給下游 agent 看的。

| 欄 | 值 |
| --- | --- |
| 破音字 | 校準 jiào |
"""


def selftest():
    """跨行【畫面】曾經被靜悄悄吃掉，吃的還是授權署名。這裡守住。"""
    data = parse_script(SELFTEST_MD)
    scenes = [d for d in data if d["type"] == "scene"]
    assert len(scenes) == 3, f"預期 3 個場景，實得 {len(scenes)}"
    blocks = scenes[0]["blocks"]
    assert len(blocks) == 2, f"預期 2 組 block，實得 {len(blocks)}"

    # 連續兩張【畫面】卡（中間刻意沒有旁白）不可以互相覆蓋。
    # EP07 因為這個 bug 掉了 7 個【畫面】區塊。
    cards = [b["screen"] for b in scenes[1]["blocks"] if b["screen"]]
    assert len(cards) == 2, f"連續畫面卡被吃掉了，預期 2 張，實得 {len(cards)}"
    assert "第一張卡" in cards[0] and "第二張卡" in cards[1], "連續畫面卡的順序或內容不對"

    # 沒有任何標記的段落（製作註記）要原樣留著。
    # 它是 vid-voice / vid-animator / vid-seo 的開工依據，掉了三個 agent 一起做錯。
    notes = scenes[2]
    assert not notes["blocks"], "製作註記不該被解析成 block"
    assert "破音字" in notes["prose"], "製作註記整段被吃掉了"
    assert "校準 jiào" in notes["prose"], "製作註記的表格內容被吃掉了"

    # 續行必須完整保留
    assert "續行一" in blocks[1]["screen"], "跨行【畫面】的續行被吃掉了"
    assert "續行二" in blocks[1]["screen"], "跨行【畫面】的續行被吃掉了"
    # 旁白不得混入動畫指示
    for b in blocks:
        assert "【畫面】" not in b["narration"], "旁白吞進了畫面指示"
    assert blocks[0]["narration"] == "第一段旁白。"
    assert blocks[1]["subtitle"] == "一行字幕"

    # round-trip：重建後再解析必須完全一致
    assert parse_script(build_md(data)) == data, "parse → 匯出 → parse 不穩定"

    # 一行內容都不准少。這是上面那些個別 assert 的總量把關——
    # 個別檢查只擋得住「我想得到的那幾種」，這條擋的是「還沒想到的那些」。
    problems = assert_roundtrip_lossless(SELFTEST_MD)
    assert not problems, "；".join(problems)

    # 陰性對照：把修好的條件拿掉，selftest 必須失敗。
    # 不驗這件事的話，「測試通過」有可能只是因為它根本沒在量。
    broken = SELFTEST_MD.replace("**【畫面】** 第二張卡", "**【畫面】** 覆蓋測試")
    lost = assert_roundtrip_lossless(broken.replace("## 製作註記（不進畫面、不唸）\n", ""))
    assert lost, "陰性對照沒有失敗——代表這支檢查其實沒在量東西"

    print("✓ selftest 通過：跨行【畫面】保住、連續卡不互相覆蓋、"
          "製作註記整段保住、round-trip 零損失（含陰性對照）")
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
    md = md_path.read_text(encoding="utf-8")
    data = parse_script(md)
    colors = load_colors()
    title = f"EP{args.ep}"
    for item in data:
        if item["type"] == "head":
            m = re.search(r'^#\s*(.+)', item["text"])
            if m:
                title = m.group(1).strip()
            break
    # localStorage key 綁定「內容雜湊」：md 一改，key 就變，舊草稿自動失效、
    # 重新載入最新 ORIGINAL（避免使用者看到被舊草稿蓋住的過時版本）。
    content_hash = hashlib.md5(md.encode("utf-8")).hexdigest()[:8]
    epkey = f"ep{epnn}-script-{content_hash}"
    dlname = f"ep{epnn}-script-edited.md"
    out = md_path.parent / f"ep{epnn}-script-editor.html"
    out.write_text(build_html(data, colors, title, epkey, dlname), encoding="utf-8")
    scenes = sum(1 for it in data if it["type"] == "scene")
    words = sum(len(re.sub(r'\s', '', b.get("narration", "")))
                for it in data if it["type"] == "scene"
                for b in it.get("blocks", []))
    print(f"✓ 已生成 {out}")
    cpm = chars_per_min()
    print(f"  場景數：{scenes}｜旁白約 {words} 字｜約 {words / cpm:.1f} 分"
          f"（{cpm:.0f} 字/分，實測 @ speed {cpm / (BASE_CPS * 60):.2f}）")
    problems = assert_license_survives(md) + assert_roundtrip_lossless(md)
    for p_ in problems:
        print("  " + p_)
    if problems:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
