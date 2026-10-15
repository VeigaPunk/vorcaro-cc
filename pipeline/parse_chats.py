import re, json, subprocess
PDF='../vorcaro.pdf'
toc=subprocess.run(['pdftotext','-layout','-f','2','-l','2',PDF,'-'],capture_output=True,text=True).stdout
convs=[]
for l in toc.splitlines():
    m=re.match(r'^\s*(\d{1,4})\s+([\d.]+)\s+(.+?)\s{2,}(\S.*)$',l)
    if m and int(m[1])<1086: convs.append((int(m[1]),m[3].strip(),m[4].strip()))
convs.sort()
recs=[]; TIME=re.compile(r'^(\d\d:\d\d:\d\d)\s+(.*)$'); DATE=re.compile(r'^\s+(\d{4}-\d\d-\d\d)\s*$')
for ci,(start,name,kind) in enumerate(convs):
    end=convs[ci+1][0]-1 if ci+1<len(convs) else 1085
    txt=subprocess.run(['pdftotext','-layout','-f',str(start),'-l',str(end),PDF,'-'],capture_output=True,text=True).stdout
    parts=[name,'DV']; date=None; cur=None
    for pi,ptxt in enumerate(txt.split('\f')):
        page=start+pi
        for l in ptxt.splitlines():
            if not l.strip() or 'Public archive compiled' in l or re.search(r'\s{5,}Transcript\s*$',l): continue
            if l.startswith('Participants:'):
                parts=sorted([p.strip() for p in l[13:].split(',')],key=len,reverse=True); continue
            m=DATE.match(l)
            if m: date=m[1]; cur=None; continue
            m=TIME.match(l)
            if m and date:
                rest=m[2]; snd=next((p for p in parts if rest.startswith(p+' ') or rest==p),rest.split(' ')[0])
                cur={'id':len(recs),'conv':name,'kind':kind,'date':date,'time':m[1],'sender':snd,'text':rest[len(snd):].strip(),'page':page}
                recs.append(cur); continue
            if cur and l.startswith(' '): cur['text']+=' '+l.strip()
for r in recs: r['ipj']=re.findall(r'\(IPJ p\.\d+[^)]*\)',r['text']); r['text']=re.sub(r'\s*\(IPJ p\.\d+[^)]*\)','',r['text']).strip()
json.dump(recs,open('data/messages.json','w'),ensure_ascii=False)
from collections import Counter
print(len(recs)); print(Counter(r['conv'] for r in recs).most_common(30)); print(Counter(r['sender'] for r in recs).most_common(10)); print(recs[100],recs[-1])
