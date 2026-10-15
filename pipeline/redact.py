"""Redaction + audit. Fail-closed: audit() returns hits; build aborts if any."""
import re
R='[REDACTED]'
MEDIA=re.compile(r'\b\d{8}-(?:PHOTO|AUDIO|VIDEO|STICKER|GIF|DOCUMENT|CONTACT)-[\d\- ]+\.\w{2,4}')
SUBS=[
 ('email', re.compile(r'[\w.+-]+\s?@\s?[\w-]{2,}(?:\.[\w-]+)*\.[A-Za-z]{2,}\b')),
 ('cpf', re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')),
 ('cnpj', re.compile(r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b')),
 ('cep', re.compile(r'\b\d{5}-\d{3}\b')),
 ('bank', re.compile(r'(?i)\b(ag[eê]ncia|ag\.|conta(?:\s+corrente)?|c/c|chave\s+pix|pix|iban|swift|routing|account\s+(?:number|no\.?))\s*(?:n[ºo°]\.?)?\s*:?\s*[\dX][\dX\-./ ]{2,}')),
 ('device', re.compile(r'(?i)\b(imei\s*[ab]?|n[uú]mero de s[eé]rie|serial(?:\s+number)?|udid|iccid|imsi)\s*:?\s*[A-Z0-9-]{5,}')),
 ('ufed', re.compile(r'(?i)\b[\w.]*(?:ufed|serviceidentifier|servicel?dentifier|participant\s+identifier)[\w.]*\s*:?\s*(?:[\w@.\-]*\d[\w@.\-]*\s*){0,2}')),
 ('hexid', re.compile(r'\b(?=[0-9a-fA-F-]*\d)[0-9a-fA-F]{8}(?:-?[0-9a-fA-F]{4}){3}-?[0-9a-fA-F]{12}\b|\b(?=[0-9a-fA-F]*[a-fA-F])(?=[0-9a-fA-F]*\d)[0-9a-fA-F]{16,}\b')),
 ('address', re.compile(r'\b(?:Rua|R\.|Avenida|Av\.|Alameda|Al\.|Travessa|Rodovia|Estrada|Praça|SHIS|SHIN|SQS|SQN|SMDB|QI|QL)\s+[^\n,;|\\]{2,60},?\s*(?:n[ºo°]\.?\s*)?\d+[\w\- ]{0,15}')),
 ('address_en', re.compile(r'\b\d{1,6}\s+(?:[NSEW]\.?\s+)?(?:[A-Z][\w.]*\s+){1,4}(?:Blvd|Boulevard|Street|St|Ave|Avenue|Road|Rd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl|Terrace|Causeway|Parkway|Hwy|Highway)\b\.?')),
 ('address_en2', re.compile(r'\b(?:[A-Z][\w.]*\s+){1,3}(?:Blvd|Boulevard)\b')),
]
KEEP=re.compile(r'^(?:\d{4}-\d\d-\d\d|\d\d/\d\d/\d{4}|\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+,\d{2})$')
WHITELIST={'3298613/2026','2026.0098110','144738439.2026','4473731/2025','4281/2025','3259365/2026','2026.0053200'}
NUM=re.compile(r'\+?\(?\d[\d\s().\-/]{6,}\d')
def _num(m):
    s=m.group(0); d=re.sub(r'\D','',s)
    if len(d)<8 or s.strip() in WHITELIST or KEEP.match(s.strip()): return s
    if re.fullmatch(r'\d{4}-\d\d-\d\d[ T]?\d?\d?:?',s) or re.search(r'\d\d/\d\d/\d{4}',s) and len(d)<=14: return s
    if re.search(r'\d{1,3}(\.\d{3})+,\d{2}',s): return s   # money
    if re.fullmatch(r'\d{1,2}:\d\d(:\d\d)?',s): return s
    return R
def redact(t):
    t=MEDIA.sub('[media]',t)
    for _,rx in SUBS: t=rx.sub(R,t)
    t,keep=_protect(t)
    t=NUM.sub(_num,t)
    return _restore(t,keep)
PROT=re.compile(r'\b(?:'+'|'.join(re.escape(w) for w in WHITELIST)+r')\b|\b\d{4}-\d\d-\d\d(?:[ T]\d\d:\d\d(?::\d\d)?)?|\b\d\d/\d\d/\d{4}(?: \d\d:\d\d(?::\d\d)?)?|\b\d\d:\d\d:\d\d\b|\b\d{1,3}(?:\.\d{3})+,\d{2}\b')
def _protect(t):
    keep=[]
    def f(m): keep.append(m.group(0)); return f'\x00{len(keep)-1}\x01'
    return PROT.sub(f,t),keep
def _restore(t,keep): return re.sub(r'\x00(\d+)\x01',lambda m:keep[int(m[1])],t)
def audit(t):
    hits={}
    t2=t.replace(R,' ')
    for name,rx in SUBS:
        n=len(rx.findall(t2)); 
        if n: hits[name]=n
    t3,_=_protect(t2); n=sum(1 for m in NUM.finditer(t3) if _num(m)==R)
    if n: hits['phone/long-number']=n
    return hits

# keyword-list junk filter (forensic table labels)
KW_JUNK=re.compile(r'(?i:ufed|identif|servic|screenshot)|\d|\||^[A-Z &/•*:]{4,}$')
