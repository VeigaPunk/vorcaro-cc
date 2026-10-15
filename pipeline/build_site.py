"""Build static site data: redact -> embed with multilingual-e5-small -> int8 -> calibrate."""
import json, re, random, sys, os, numpy as np, torch
sys.path.insert(0,os.path.dirname(__file__)); from redact import redact, audit, R, KW_JUNK as JUNK
SRC=sys.argv[1] if len(sys.argv)>1 else '../vorcaro-search/data'; OUT='docs/data'; os.makedirs(OUT,exist_ok=True)
docs=json.load(open(f'{SRC}/docs.json')); kws=json.load(open(f'{SRC}/keywords.json'))
out=[]
for d in docs:
    t=redact(d['text'])
    if len(re.sub(r'\[REDACTED\]|\W','',t))<3: continue
    out.append({'c':redact(d['conv']),'d':d['date'],'t':d['time'],'s':[redact(x) for x in d['senders']],'p':d['page'],'x':t,'i':[redact(x) for x in d['ipj']]})
kout=[{'k':redact(k['name']),'n':k['count'],'l':k['label']} for k in kws if not JUNK.search(k['name'])]
kout=[k for k in kout if R not in k['k']]
from sentence_transformers import SentenceTransformer
M='intfloat/multilingual-e5-small'
m=SentenceTransformer(M,device='cuda'); m.max_seq_length=512
enc=lambda xs,p,bs=128: m.encode([p+x for x in xs],batch_size=bs,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)
E=enc([d['x'] for d in out],'passage: '); K=enc([k['k'] for k in kout],'query: ')
c=E.mean(0); c/=np.linalg.norm(c); hub=E@c; hub=hub-hub.mean()
ALPHA=0.3
vocab=sorted({w.lower() for d in random.Random(0).sample(out,4000) for w in re.findall(r'[A-Za-zÀ-ú]{4,}',d['x'])})
q=random.Random(1).sample(vocab,1500)+[k['k'] for k in random.Random(2).sample(kout,min(500,len(kout)))]
Q=enc(q,'query: ')
null=(Q@E.T-ALPHA*hub[None,:]).ravel()
P=[0.5,0.9,0.99,0.999,0.9999,0.99999]
qs=[round(x,5) for x in np.quantile(null,P).tolist()]
# keyword null: exclude exact self matches
nk=Q@K.T; nk=nk[nk<0.999]; kqs=[round(x,5) for x in np.quantile(nk,P).tolist()]
def q8(A):
    s=float(np.abs(A).max()); return (np.round(A/s*127).astype(np.int8)), s
Eq,es=q8(E); Kq,ks=q8(K)
Eq.tofile(f'{OUT}/doc_emb.i8'); Kq.tofile(f'{OUT}/kw_emb.i8')
for i,d in enumerate(out): d['h']=round(float(hub[i]),4)
json.dump(out,open(f'{OUT}/docs.json','w'),ensure_ascii=False,separators=(',',':'))
json.dump(kout,open(f'{OUT}/keywords.json','w'),ensure_ascii=False,separators=(',',':'))
meta={'model':'Xenova/multilingual-e5-small','py_model':M,'dim':int(E.shape[1]),'n_docs':len(out),'n_kw':len(kout),'doc_scale':round(es,6),'kw_scale':round(ks,6),
 'hub_alpha':ALPHA,'lex_bonus':0.02,'null_probs':P,'pct_at':[50,75,90,95,97,99],'doc_null_quantiles':qs,'kw_null_quantiles':kqs}
json.dump(meta,open(f'{OUT}/meta.json','w'),indent=1)
print(meta)
