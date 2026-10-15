import sys, json
from flask import Flask, request, jsonify, Response
from engine import Engine
E=Engine(); app=Flask(__name__)
HTML='''<!doctype html><meta charset=utf-8><title>Vorcaro relatedness search</title>
<style>body{font-family:system-ui;max-width:1000px;margin:20px auto;background:#111;color:#ddd}input[type=text]{width:60%;font-size:18px;padding:6px}
.r{border-bottom:1px solid #333;padding:8px 0}.p{font-weight:bold;display:inline-block;width:60px}.m{color:#8ab}.t{white-space:pre-wrap;margin-top:4px;font-size:14px}
.k{display:inline-block;margin:2px;padding:2px 6px;border-radius:8px;background:#234;cursor:pointer}.bar{height:4px;background:#4a8}</style>
<h2>Vorcaro archive — relatedness search</h2>
<form onsubmit="go();return false"><input type=text id=q placeholder="anything: restaurante, dinner in Paris, Banco Central…" autofocus> <button>Search</button><br>
threshold <input type=range id=th min=50 max=100 step=1 value=90 oninput="tv.textContent=this.value+'%'"><span id=tv>90%</span> &nbsp; max <input id=lim value=100 size=4></form>
<div id=kw></div><div id=info></div><div id=res></div>
<script>
const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
async function go(){const q=document.getElementById('q').value;if(!q)return;
const r=await (await fetch('/api/search?q='+encodeURIComponent(q)+'&threshold='+th.value+'&limit='+lim.value)).json();
kw.innerHTML='Related keywords: '+r.related_keywords.map(k=>`<span class=k onclick="q.value='${esc(k.keyword).replace(/'/g,"")}';go()">${esc(k.keyword)} ${k.pct.toFixed(0)}%</span>`).join('');
info.innerHTML=`<p>${r.n_above} passages ≥ ${r.threshold}% (showing ${r.results.length})</p>`;
res.innerHTML=r.results.map(h=>`<div class=r><div class=bar style="width:${h.pct}%"></div><span class=p>${h.pct.toFixed(1)}%</span><span class=m>${esc(h.conv)} · ${h.date} ${h.time} · ${esc(h.senders.join(', '))} · PDF p.${h.page} ${esc(h.ipj.join(' '))}</span><div class=t>${esc(h.text)}</div></div>`).join('')}
th.onchange=go;
</script>'''
@app.get('/')
def index(): return Response(HTML,mimetype='text/html')
@app.get('/api/search')
def api():
    return jsonify(E.search(request.args.get('q',''),float(request.args.get('threshold',90)),int(request.args.get('limit',100))))
if __name__=='__main__': app.run('127.0.0.1',int(sys.argv[1]) if len(sys.argv)>1 else 8790,threaded=True)
