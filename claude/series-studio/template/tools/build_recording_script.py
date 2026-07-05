#!/usr/bin/env python3
"""
build_recording_script.py — 本人配音用「錄音唸稿」HTML（所有系列共用）

把 episodes/epNN/script/epNN-script.md 轉成適合「對著唸錄音」的唸稿：
- 只顯示場景標題 ＋ 大字旁白（拿掉畫面/字幕等干擾），易讀好唸
- 每段標好建議錄音檔名（epNN-sceneNN.wav），點一下可複製
- 每段可勾「✓ 已錄」，進度存 localStorage（頂部顯示已錄 X/N）
- 每段顯示預估秒數；配色自動套 series.yaml 的 visual token

用法：python3 tools/build_recording_script.py --ep N
輸出：episodes/epNN/script/epNN-錄音稿.html
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_script_editor import parse_script, load_colors  # noqa: E402


def scene_no(title):
    m = re.search(r'##\s*(\d+)', title)
    return m.group(1) if m else "XX"


TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>__TITLE__ — 錄音唸稿</title>
<style>
  :root{__ROOTVARS__}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:"Noto Sans TC","PingFang TC",sans-serif;line-height:1.95}
  header{position:sticky;top:0;z-index:10;background:var(--bg);
    border-bottom:1px solid var(--line);padding:14px 22px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
  header h1{font-size:17px;margin:0;font-weight:900}
  .stat{font-size:14px;color:var(--muted)}
  .stat b{color:var(--teal);font-size:16px}
  main{max-width:880px;margin:0 auto;padding:24px 20px 140px}
  .tip{background:var(--code);border:1px dashed var(--line);border-radius:12px;
    padding:14px 18px;color:var(--muted);font-size:14px;margin-bottom:22px;line-height:1.7}
  .tip b{color:var(--accent)}
  .scene{background:var(--surface);border:1px solid var(--line);border-radius:16px;
    padding:22px 24px;margin-bottom:22px;transition:opacity .2s}
  .scene.done{opacity:.5}
  .scene-head{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px;
    border-bottom:1px solid var(--line);padding-bottom:12px}
  .scene-title{font-size:20px;font-weight:900;color:var(--accent);flex:1;min-width:200px}
  .fname{font-family:"JetBrains Mono",monospace;font-size:13px;background:var(--code);
    color:var(--teal);padding:4px 10px;border-radius:7px;cursor:pointer;border:1px solid var(--line)}
  .fname:hover{filter:brightness(1.2)}
  .secs{font-size:12px;color:var(--muted)}
  .done-btn{font-family:inherit;cursor:pointer;border:1px solid var(--line);border-radius:8px;
    padding:6px 12px;font-size:13px;font-weight:700;background:var(--code);color:var(--muted)}
  .done-btn.on{background:var(--teal);color:var(--bg);border-color:var(--teal)}
  .narr{font-size:21px;line-height:2.1;color:var(--text);white-space:pre-wrap}
  .marker{text-align:center;color:var(--muted);font-size:14px;border:1px dashed var(--primary);
    border-radius:12px;padding:12px;margin-bottom:22px}
  .toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--teal);
    color:var(--bg);padding:10px 20px;border-radius:10px;font-weight:700;opacity:0;transition:opacity .2s;pointer-events:none}
  .toast.show{opacity:1}
</style>
</head>
<body>
<header>
  <h1>__TITLE__ <span style="color:var(--primary)">· 錄音唸稿</span></h1>
  <span class="stat">已錄 <b id="doneCount">0</b>/<b id="total">0</b> 段 · 全長約 <b id="totalTime">0</b> 分</span>
</header>
<main id="main"></main>
<div class="toast" id="toast">已複製檔名</div>
<script>
const DATA = __DATA__;
const KEY = "__EPKEY__";
const EP = "__EPNN__";
let done = load();
function load(){ try{ const s=localStorage.getItem(KEY); if(s) return JSON.parse(s);}catch(e){} return {}; }
function save(){ localStorage.setItem(KEY, JSON.stringify(done)); }
function wc(t){ return (t||"").replace(/\s/g,"").length; }
function secs(t){ return Math.round(wc(t)/4.3); }
function toast(msg){ const t=document.getElementById('toast'); t.textContent=msg; t.classList.add('show');
  clearTimeout(window._t); window._t=setTimeout(()=>t.classList.remove('show'),1200); }
function render(){
  const main=document.getElementById('main'); main.innerHTML="";
  const tip=document.createElement('div'); tip.className="tip";
  tip.innerHTML='對著大字旁白唸即可。每段一個檔：點<b>檔名</b>可複製，存成 wav（48kHz/單聲道佳）放到 <b>episodes/ep'+EP+'/voiceover/</b>。唸錯就整句重來、後製再剪。錄完一段就按 <b>✓ 已錄</b> 記進度。';
  main.appendChild(tip);
  let total=0, doneN=0, totSec=0;
  DATA.forEach(item=>{
    if(item.type!=="scene"){
      if(item.type==="marker"){ const d=document.createElement('div'); d.className="marker"; d.textContent="（"+item.text.replace(/[〔〕]/g,"")+" — 此處不錄）"; main.appendChild(d); }
      return;
    }
    total++; totSec+=secs(item.narration);
    const no=item.no; const fname="ep"+EP+"-scene"+no+".wav";
    const isDone=!!done[no]; if(isDone) doneN++;
    const card=document.createElement('div'); card.className="scene"+(isDone?" done":"");
    const head=document.createElement('div'); head.className="scene-head";
    const tt=document.createElement('div'); tt.className="scene-title"; tt.textContent=item.title.replace(/^##\s*/,'');
    const fn=document.createElement('span'); fn.className="fname"; fn.textContent=fname;
    fn.onclick=()=>{ navigator.clipboard.writeText(fname).then(()=>toast("已複製 "+fname)); };
    const sc=document.createElement('span'); sc.className="secs"; sc.textContent="約 "+secs(item.narration)+" 秒";
    const db=document.createElement('button'); db.className="done-btn"+(isDone?" on":""); db.textContent=isDone?"✓ 已錄":"標記已錄";
    db.onclick=()=>{ done[no]=!done[no]; save(); render(); };
    head.appendChild(tt); head.appendChild(fn); head.appendChild(sc); head.appendChild(db); card.appendChild(head);
    const nr=document.createElement('div'); nr.className="narr"; nr.textContent=item.narration; card.appendChild(nr);
    main.appendChild(card);
  });
  document.getElementById('total').textContent=total;
  document.getElementById('doneCount').textContent=doneN;
  document.getElementById('totalTime').textContent=(totSec/60).toFixed(1);
}
render();
</script>
</body>
</html>
'''


def build_html(data, colors, title, epkey, epnn):
    rootvars = ";".join(f"--{k}:{v}" for k, v in [
        ("primary", colors["primary"]), ("accent", colors["accent"]), ("teal", colors["teal"]),
        ("bg", colors["bg"]), ("surface", colors["surface"]), ("code", colors["code"]),
        ("text", colors["text"]), ("muted", colors["muted"]), ("line", colors["line"]),
    ])
    # 給每個 scene 標場景號
    for it in data:
        if it["type"] == "scene":
            it["no"] = scene_no(it["title"])
    html = TEMPLATE
    html = html.replace("__ROOTVARS__", rootvars)
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    html = html.replace("__EPKEY__", epkey)
    html = html.replace("__EPNN__", epnn)
    html = html.replace("__TITLE__", title)
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, required=True)
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
    content_hash = hashlib.md5(md.encode("utf-8")).hexdigest()[:8]
    epkey = f"ep{epnn}-recording-{content_hash}"
    out = md_path.parent / f"ep{epnn}-錄音稿.html"
    out.write_text(build_html(data, colors, title, epkey, epnn), encoding="utf-8")
    scenes = sum(1 for it in data if it["type"] == "scene")
    print(f"✓ 已生成 {out}")
    print(f"  {scenes} 段要錄（ep{epnn}-scene00.wav … ）")


if __name__ == "__main__":
    main()
