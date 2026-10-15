"""Fail-closed regex audit over every file to be published."""
import os, sys, json
sys.path.insert(0,os.path.dirname(__file__)); from redact import audit
root=sys.argv[1] if len(sys.argv)>1 else '.'; tot={}; bad=[]
for dp,dn,fn in os.walk(root):
    dn[:]=[d for d in dn if d not in('.git',)]
    for f in fn:
        p=os.path.join(dp,f)
        if p.endswith('.i8'): continue  # binary int8 vectors, no text
        h=audit(open(p,encoding='utf-8',errors='ignore').read())
        if p.endswith(('redact.py','audit.py')): h={}  # pattern source, not data
        for k,v in h.items(): tot[k]=tot.get(k,0)+v
        if h: bad.append((p,h))
print(json.dumps({'files_checked':sum(len(f) for _,_,f in os.walk(root)),'hits':tot,'bad_files':bad},ensure_ascii=False))
sys.exit(1 if tot else 0)
