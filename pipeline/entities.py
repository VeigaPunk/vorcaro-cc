# keyword/entity extraction over messages + report chunks
import json, re, spacy, collections, sys
msgs=json.load(open('data/messages.json'))
try: chunks=json.load(open('data/report_chunks.json'))
except: chunks=[]
nlp=spacy.load('pt_core_news_lg',disable=['parser','lemmatizer'])
docs=[('m',m['id'],m['text']) for m in msgs if len(m['text'])>2 and not m['text'].startswith('[')]+[('r',c['id'],c['text']) for c in chunks]
STOP=set('DV Kkk Kkkk Kkkkk Amor Bom Boa Oi Ok Sim Não Nao Te Vc Você Hahaha Hahahaha Amorrr Vida Ta Tá Eu Ele Ela Que Mas Meu Minha Gente Deus Obrigado Obrigada Beijo Beijos Bjs Tb Também E O A Os As Já Ja Hoje Amanhã Agora Aqui Lá Muito Demais Nossa Pq Vamos Vou Acho Tudo Mto Hj Lindo Linda Saudade Saudades Dorme Noite Dia Kkkkkk Hahah Haha Tô To Isso Esse Essa Partner Love Amore Bebe Bebê Kk Mensagem'.split())
ent=collections.defaultdict(lambda:{'count':0,'label':collections.Counter(),'occ':[]})
def add(name,label,src,i):
    name=re.sub(r'\s+',' ',name).strip(' .,:;!?"\'()-'); 
    if len(name)<3 or name in STOP or name.lower() in {s.lower() for s in ()} or re.fullmatch(r'[\d\W]+',name): return
    e=ent[name]; e['count']+=1; e['label'][label]+=1
    if len(e['occ'])<200: e['occ'].append([src,i])
VENUE=re.compile(r'(?i:\b(restaurante|rest\.|hotel|hotél|bar|café|cafe|trattoria|osteria|steakhouse|churrascaria|bistr[oô]|clube|club|resort|pousada|jantar no|jantar na|almoço no|almoço na|almocar no|jantar em))\s+((?:[A-ZÀ-Ú][\w\'’&À-ú-]*\s?){1,4})')
MONEY=re.compile(r'(?:R\$|US\$|U\$|\$|€|EUR|USD)\s?\d[\d.,]*\s*(?:mil|mi|milh[õo]es|bi|bilh[õo]es|k|M)?|\b\d[\d.,]*\s*(?:mil reais|milh[õo]es|bilh[õo]es|mi\b|bi\b|reais|d[óo]lares|euros)',re.I)
texts=[t for _,_,t in docs]
for (src,i,t),d in zip(docs,nlp.pipe(texts,batch_size=512,n_process=16)):
    for e in d.ents:
        if e.label_ in('PER','LOC','ORG','MISC'): add(e.text,e.label_,src,i)
    for m in VENUE.finditer(t):
        kind=m[1].lower(); kind='HOTEL' if kind.startswith('hot') or kind in('resort','pousada') else 'VENUE'
        add(m[2].strip(),kind,src,i)
    for m in MONEY.finditer(t): add(m[0].strip(),'AMOUNT',src,i)
import unicodedata
def norm(x): return ''.join(c for c in unicodedata.normalize('NFD',x.lower()) if unicodedata.category(c)!='Mn')
# capitalization ratio mid-sentence
cap=collections.Counter(); tot=collections.Counter()
for _,_,t in docs:
    toks=re.findall(r'[\wÀ-ú]+',t)
    for w in toks[1:]:
        n=norm(w); tot[n]+=1
        if w[0].isupper(): cap[n]+=1
FOOD=re.compile(r'(?i)\b(jantar|janta|almo[çc]o|almo[çc]ar|restaurante|reserva|mesa|comer|comida|drink|vinho|caf[ée] da manh[ãa]|brunch|dinner|lunch|chef|menu|card[áa]pio)\b')
food_ids={('m',m['id']) for m in msgs if FOOD.search(m['text'])}
nb=collections.defaultdict(set)
for m in msgs:
    if FOOD.search(m['text']):
        for d in range(-3,4): nb['m'].add(m['id']+d)
merged={}
for k,v in ent.items():
    if re.search(r'(.)\1\1',k.lower()) or re.search(r'(?i)^(k+|(ha)+h?|(he)+|rs+)$',k) or 'call' in k.lower() or 'message' in k.lower(): continue
    n=norm(k); toks=n.split()
    if (k.isupper() and len(toks)>1) or len(toks)>4 or set(toks)&{'amor','voce','pra','to','ta','deus','saudade','oi','sorry','desculpe','mentira','liga','page','ok','te','vou','i','it','the','acabei','louca','cade','me','ja','so','tambem','minha','meu','mae','dr','senhor','parabens'}: continue
    if 'AMOUNT' not in v['label']:
        if len(toks)==1 and (tot[n]<3 or cap[n]/max(1,tot[n])<0.4): continue
        if all(len(t)<=3 for t in toks) or n in {norm(x) for x in STOP}: continue
    g=merged.setdefault(n,{'forms':collections.Counter(),'count':0,'label':collections.Counter(),'occ':[]})
    g['forms'][k]+=v['count']; g['count']+=v['count']; g['label'].update(v['label']); g['occ']+=v['occ'][:200-len(g['occ'])] if len(g['occ'])<200 else []
ent={}
for n,g in merged.items():
    fc=sum(1 for s,i in g['occ'] if s=='m' and i in nb['m'])/max(1,len(g['occ']))
    lab=g['label'].most_common(1)[0][0]
    ent[g['forms'].most_common(1)[0][0]]={'count':g['count'],'label':g['label'],'occ':g['occ'],'food_ctx':round(fc,2)}
out=[]
for k,v in ent.items():
    if v['count']<2 and 'AMOUNT' not in v['label']: continue
    out.append({'name':k,'count':v['count'],'label':v['label'].most_common(1)[0][0],'labels':dict(v['label']),'occ':v['occ'],'food_ctx':v['food_ctx']})
out.sort(key=lambda x:-x['count'])
json.dump(out,open('data/entities.json','w'),ensure_ascii=False)
print('FOODCTX',[(e['name'],e['count'],e['food_ctx']) for e in out if e['label'] in('LOC','ORG','MISC','VENUE','HOTEL','PER') and e['count']>=4 and e['food_ctx']>=0.5][:60])
for L in ['PER','LOC','ORG','VENUE','HOTEL','AMOUNT','MISC']:
    print(L,[(e['name'],e['count']) for e in out if e['label']==L][:40])
