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


def parse_script(md):
    """把腳本 md 解析成 [{type, ...}]。type: head/scene/marker/license。"""
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

    def new_block():
        return {"screen": "", "subtitle": "", "narration": ""}

    def close_block():
        """把當前 block 收進場景（空 block 不收）。"""
        nonlocal blk
        if cur is not None and blk and (blk["screen"] or blk["subtitle"] or blk["narration"]):
            cur["blocks"].append(blk)
        blk = None

    def flush():
        nonlocal cur, blk
        if cur:
            close_block()
            data.append(cur)
            cur = None
        blk = None

    while i < n:
        line = lines[i]
        s = line.strip()
        if line.startswith("## "):
            flush()
            cur = {"type": "scene", "title": line.rstrip(), "blocks": []}
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
            # 每收完一段旁白就算一組結束，下一個【畫面】/【字幕】開新的一組。
            if line.startswith("**【畫面】**"):
                if blk is None or blk["narration"]:
                    close_block()
                    blk = new_block()
                blk["screen"] = re.sub(r'^\*\*【畫面】\*\*\s*', '', line).strip()
                i += 1
                continue
            if line.startswith("**【字幕】**"):
                if blk is None or blk["narration"]:
                    close_block()
                    blk = new_block()
                blk["subtitle"] = re.sub(r'^\*\*【字幕】\*\*\s*', '', line).strip()
                i += 1
                continue
            if line.startswith("**【旁白】**"):
                if blk is None:
                    blk = new_block()
                i += 1
                narr = []
                while i < n:
                    l2 = lines[i]
                    s2 = l2.strip()
                    # ⚠️ 必須在下一個【畫面】/【字幕】/【旁白】就停，
                    # 否則旁白會把整個場景剩下的動畫指示全吞進去。
                    if (s2 == "---" or l2.startswith("## ")
                            or l2.startswith("**【")
                            or (s2.startswith("〔") and s2.endswith("〕"))):
                        break
                    narr.append(l2)
                    i += 1
                blk["narration"] = "\n".join(narr).strip()
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
    const card=document.createElement('div'); card.className="scene";
    const t=document.createElement('input'); t.className="scene-title"; t.value=item.title;
    t.oninput=()=>{item.title=t.value; save();}; card.appendChild(t);
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
  document.getElementById('totalTime').textContent=(tot/(4.3*60)).toFixed(1); }
function buildMd(){ let out=[];
  data.forEach(item=>{
    if(item.type==="head"){ out.push(item.text+"\n\n---"); }
    else if(item.type==="marker"){ out.push("\n"+item.text+"\n\n---"); }
    else if(item.type==="license"){ out.push("\n"+item.text); }
    else{ let s="\n"+item.title+"\n";
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
    html = html.replace("__DLNAME__", dlname)
    html = html.replace("__TITLE__", title)
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, required=True, help="集數 N")
    args = ap.parse_args()
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
    print(f"  場景數：{scenes}｜旁白約 {words} 字｜約 {words / (4.3 * 60):.1f} 分")


if __name__ == "__main__":
    main()
