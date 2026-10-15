import json, numpy as np, torch, random, re
from sentence_transformers import SentenceTransformer
msgs=json.load(open('data/messages.json')); chunks=json.load(open('data/report_chunks.json')); ents=json.load(open('data/entities.json'))
# windows: consecutive msgs same conv+date, gap<=15min, <=8 msgs, <=600 chars
def sec(t): h,m,s=map(int,t.split(':')); return h*3600+m*60+s
docs=[]; w=[]
def flush():
    if w:
        docs.append({'type':'chat','conv':w[0]['conv'],'date':w[0]['date'],'time':w[0]['time'],'senders':sorted({m['sender'] for m in w}),'page':w[0]['page'],'msg_ids':[m['id'] for m in w],
          'text':'\n'.join(f"{m['sender']}: {m['text']}" for m in w),'ipj':sorted({x for m in w for x in m['ipj']})})
for m in msgs:
    if w and (m['conv']!=w[-1]['conv'] or m['date']!=w[-1]['date'] or sec(m['time'])-sec(w[-1]['time'])>900 or len(w)>=8 or sum(len(x['text']) for x in w)>600): flush(); w=[]
    w.append(m)
flush()
for c in chunks: docs.append({'type':'report','conv':'IPJ-A 3298613/2026 (PF report)','date':'2026-08-27','time':'','senders':['Polícia Federal'],'page':c['page'],'text':c['text'],'ipj':[]})
print('docs',len(docs))
model=SentenceTransformer('BAAI/bge-m3',device='cuda',model_kwargs={'torch_dtype':torch.float16}); model.max_seq_length=512
E=model.encode([d['text'] for d in docs],batch_size=128,normalize_embeddings=True,show_progress_bar=True,convert_to_numpy=True).astype(np.float16)
kw=[e for e in ents if e['count']>=3 and e['label']!='AMOUNT'][:6000]
K=model.encode([e['name'] for e in kw],batch_size=256,normalize_embeddings=True,convert_to_numpy=True).astype(np.float16)
# null distribution: random short queries (vocab words + entity names) vs random docs
vocab=sorted({w.lower() for d in random.Random(0).sample(docs,4000) for w in re.findall(r'[A-Za-zÀ-ú]{4,}',d['text'])})
q=random.Random(1).sample(vocab,min(1500,len(vocab)))+[e['name'] for e in random.Random(2).sample(kw,min(500,len(kw)))]
Q=model.encode(q,batch_size=256,normalize_embeddings=True,convert_to_numpy=True)
null=(Q@E.astype(np.float32).T).ravel()
qs=np.quantile(null,[0.5,0.9,0.99,0.999,0.9999,0.99999]).tolist()
nk=(Q@K.astype(np.float32).T).ravel(); kqs=np.quantile(nk,[0.5,0.9,0.99,0.999,0.9999,0.99999]).tolist()
np.save('data/doc_emb.npy',E); np.save('data/kw_emb.npy',K)
json.dump(docs,open('data/docs.json','w'),ensure_ascii=False); json.dump([{'name':e['name'],'count':e['count'],'label':e['label']} for e in kw],open('data/keywords.json','w'),ensure_ascii=False)
json.dump({'doc_null_quantiles':qs,'kw_null_quantiles':kqs,'probs':[0.5,0.9,0.99,0.999,0.9999,0.99999],'n_null_pairs':int(null.size)},open('data/calibration.json','w'),indent=1)
print('calib',qs,kqs)
