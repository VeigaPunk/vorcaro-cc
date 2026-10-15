import re, json, glob, subprocess, os
def clean(t):
    t=re.sub(r'<\|det\|>.*?<\|/det\|>','',t); t=re.sub(r'!\[\]\([^)]*\)','',t)
    t=re.sub(r'<(/?)(table|tr)>','\n',t); t=re.sub(r'</?t[dh][^>]*>',' | ',t)
    lines=[l for l in t.splitlines() if not re.search(r'(The image (contains|shows)|According to the guidelines|no OCR output|People\'s Republic)',l)]
    return '\n'.join(lines)
chunks=[]; stats=[]
for p in range(1086,1304):
    tl=subprocess.run(['pdftotext','-f',str(p),'-l',str(p),'../vorcaro.pdf','-'],capture_output=True,text=True).stdout
    f=f'ocr/p{p:04d}.md'; oc=clean(open(f).read()) if os.path.exists(f) else ''
    words=lambda s:set(re.findall(r'\w{4,}',s.lower()))
    cov=len(words(tl)&words(oc))/max(1,len(words(tl)))
    src='ocr' if len(oc)>0.6*len(tl) and (cov>0.7 or len(tl)<200) else 'textlayer'
    txt=oc if src=='ocr' else tl+('\n[OCR figure text]\n'+oc if oc else '')
    stats.append({'page':p,'src':src,'tl':len(tl),'ocr':len(oc),'cov':round(cov,2)})
    paras=[re.sub(r'\s+',' ',x).strip() for x in re.split(r'\n\s*\n|\n(?=[A-Z0-9#])',txt)]
    buf=''
    for x in paras:
        if not x or re.fullmatch(r'(Página \d+.*|IPJ-A n.*|\W*)',x): continue
        if len(buf)+len(x)>700 and buf: chunks.append({'id':len(chunks),'page':p,'text':buf}); buf=''
        buf=(buf+' '+x).strip()
    if buf: chunks.append({'id':len(chunks),'page':p,'text':buf})
json.dump(chunks,open('data/report_chunks.json','w'),ensure_ascii=False); json.dump(stats,open('data/ocr_choice.json','w'))
import collections; print(len(chunks),collections.Counter(s['src'] for s in stats)); print([s for s in stats if s['src']=='textlayer'][:10])
