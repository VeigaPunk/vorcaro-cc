import json, numpy as np, re, unicodedata, os, torch
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'data')
PCT=[0,50,70,80,90,95,98,100]  # pct assigned at null quantiles [min,.5,.9,.99,.999,.9999,.99999,max]
LEX_BONUS=0.08
HUB_ALPHA=0.3  # hubness correction: penalise docs close to corpus centroid (short generic msgs)
def norm(x): return ''.join(c for c in unicodedata.normalize('NFD',x.lower()) if unicodedata.category(c)!='Mn')
class Engine:
    def __init__(s,device=None):
        from sentence_transformers import SentenceTransformer
        s.docs=json.load(open(f'{D}/docs.json')); s.kw=json.load(open(f'{D}/keywords.json')); s.cal=json.load(open(f'{D}/calibration.json'))
        s.E=torch.tensor(np.load(f'{D}/doc_emb.npy')).float(); s.K=torch.tensor(np.load(f'{D}/kw_emb.npy')).float()
        dev=device or ('cuda' if torch.cuda.is_available() else 'cpu')
        s.m=SentenceTransformer('BAAI/bge-m3',device=dev,model_kwargs={'torch_dtype':torch.float16} if dev=='cuda' else {})
        c=s.E.mean(0); c=c/c.norm(); s.hub=(s.E@c).numpy(); s.hub=s.hub-s.hub.mean()
        s.ntext=[norm(d['text']) for d in s.docs]
    def pct(s,cos,q):
        xs=[-1.0]+q+[max(q[-1]+0.15,1.0)]; xs[-1]=min(1.0,q[-1]+0.15)
        return np.clip(np.interp(cos,xs,PCT),0,100)
    def search(s,query,threshold=90,limit=100,kw_limit=25):
        qe=torch.tensor(s.m.encode([query],normalize_embeddings=True))[0].float()
        cos=(s.E@qe).numpy()-HUB_ALPHA*s.hub
        nq=norm(query).strip(); terms=[t for t in re.findall(r'\w{4,}',nq)]
        if nq:
            pat=re.compile(r'\b'+re.escape(nq)+r'\w{0,3}\b')
            lex=np.array([1.0 if pat.search(t) else (0.5 if terms and all(re.search(r'\b'+re.escape(w),t) for w in terms) else 0.0) for t in s.ntext])
            cos=cos+LEX_BONUS*lex
        p=s.pct(cos,s.cal['doc_null_quantiles'])
        order=np.argsort(-p); hits=[]
        for i in order[:limit]:
            if p[i]<threshold: break
            d=s.docs[i]; hits.append({'pct':round(float(p[i]),1),'cos':round(float(cos[i]),3),**{k:d[k] for k in('type','conv','date','time','senders','page','text','ipj')}})
        kc=(s.K@qe).numpy(); kp=s.pct(kc,s.cal['kw_null_quantiles'])
        ko=np.argsort(-kp)[:kw_limit]
        kws=[{'keyword':s.kw[i]['name'],'label':s.kw[i]['label'],'count':s.kw[i]['count'],'pct':round(float(kp[i]),1)} for i in ko]
        return {'query':query,'threshold':threshold,'n_above':int((p>=threshold).sum()),'results':hits,'related_keywords':kws}
