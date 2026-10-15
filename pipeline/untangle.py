"""Clean the archive for the GitHub Pages prototype and group it by concept.

Source of the words: vorcaro-search/data/messages.json (the parse before the
site redaction pass) and report_chunks.json. Published strings still go
through redact(). Phones, CPFs, bank details and street addresses do not
come back.

Windows stay in the same order as docs/data/doc_emb.i8. Display text is
cleaned; the vectors are unchanged.

  python pipeline/untangle.py            # review only
  python pipeline/untangle.py --publish  # write docs/data and stop if audit fails
"""
import json, os, re, sys, unicodedata
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from redact import redact, audit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(ROOT), 'vorcaro-search', 'data')
PUB = os.path.join(ROOT, 'docs', 'data')
BUILD = os.path.join(ROOT, 'build')

def norm(s):
    s = (s or '').replace('\u2019', "'").replace('\u2018', "'").replace('`', "'")
    s = unicodedata.normalize('NFD', s.lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')

def sec(t):
    h, m, s = map(int, t.split(':'))
    return h * 3600 + m * 60 + s

GREEK = re.compile('[ὠὡὣὢὤὃἱ]+')
DET = re.compile(r'<\|/?[^|>]{0,24}\|>')
FOOD_RE = re.compile(r'(?i)\b(restaurantes?|jantar|jantamos|jantam|janta\b|jantares|almo[cç]os?|almoc\w*|brunch|bistr[oô]s?|trattor\w*|osteri\w*|steak\s?house|churrascar\w*|rod[ií]zio|buffet|card[aá]pio|\bchef\b|reserv\w*\s+uma\s+mesa|mesa\s+no|mesa\s+na)\b')
TRAVEL_RE = re.compile(r'(?i)\b(?<!modo )(avi[aã]o|voo\b|voos|aeroporto|embarque|decol\w*|pouso|helic[oó]ptero|business\s+class|classe\s+executiva)\b')

GENERIC = set(map(norm, '''hotel hotéis hotels restaurante restaurantes bar bars casa casas lugar lugares
clube club cafe café shopping mall centro cidade rua avenida praia ilha barco piscina academia gym
mercado escritorio escritório trabalho escola quarto sala cama mesa noite tarde manha manhã hoje
amanha amanhã depois antes local ponto reunião reuniao call zoom uber carro transfer voo aviao avião
aeroporto helicóptero helicoptero spa salão salao medico médico hospital clinica clínica cabeleireiro
apartamento apto predio prédio condominio condomínio bairro frente volta caminho sitio sítio
jantar almoco almoço almoçar brunch chef menu reserva reservas hotelaria pousada resort clube
people pessoa pessoas amigo amiga grupo pessoal staff equipe festa aniversario aniversário
dia dias vez vezes hora horas semana lado cima baixo aqui ali la lá ai aí bem mal muito mais
todo toda todos tudo nada coisa coisas gente deus amor vida parceiro partner love
banco master central federal polícia policia supremo tribunal operação operacao
itau itaú whatsapp instagram nota figura submodule activity lunch cruise free event
transport departure arrival gala welcome choice onboard menu beverages style suggested
tba expected time deck dress code imagem video audio documento arquivo anexo media
redacted document text image foto fotos
'''.split()))

CITIES = [
    ('Paris', 'paris'), ('Miami', 'miami'), ('Londres', 'londres|london'), ('Roma', 'roma|rome'),
    ('Lisboa', 'lisboa|lisbon'), ('Nova York', 'nova york|new york|nyc'), ('São Paulo', 'sao paulo|sampa'),
    ('Rio de Janeiro', 'rio de janeiro'), ('Brasília', 'brasilia'), ('Belo Horizonte', r'\bbh\b|belo horizonte'),
    ('Trancoso', 'trancoso'), ('Angra', 'angra'), ('Aspen', 'aspen'), ('Dubai', 'dubai'),
    ('Orlando', 'orlando'), ('Ibiza', 'ibiza'), ('Mykonos', 'mykonos|mikonos'), ('St. Barths', 'st barths|saint barth'),
    ('Genebra', 'genebra|geneva'), ('Zurique', 'zurique|zurich'), ('Madri', 'madri|madrid'),
    ('Barcelona', 'barcelona'), ('Milão', 'milao|milan'), ('Veneza', 'veneza|venice'),
    ('Florença', 'florenca|florence'), ('Capri', 'capri'), ('Positano', 'positano'),
    ('Nice', 'nice'), ('Mônaco', 'monaco|mônaco'), ('Los Angeles', 'los angeles'),
    ('Las Vegas', 'las vegas'), ('Punta del Este', 'punta del este'), ('Búzios', 'buzios'),
    ('Paraty', 'paraty'), ('Gramado', 'gramado'), ('Campos do Jordão', 'campos do jordao'),
    ('Comporta', 'comporta'), ('Algarve', 'algarve'), ('Santorini', 'santorini'),
    ('Atenas', 'atenas|athens'), ('Istambul', 'istambul|istanbul'), ('Bahamas', 'bahamas'),
    ('Cancún', 'cancun'), ('Toscana', 'toscana|tuscany'), ('Amalfi', 'amalfi'),
    ('Fernando de Noronha', 'noronha'), ('Jericoacoara', 'jericoacoara|jeri'),
    ('Ilhabela', 'ilhabela'), ('Rio', r'\brio\b'), ('Nova Iorque', 'nova iorque'),
    ('Recife', 'recife'), ('Salvador', 'salvador'), ('Fortaleza', 'fortaleza'),
    ('Curitiba', 'curitiba'), ('Florianópolis', 'florianopolis|floripa'),
    ('Porto Alegre', 'porto alegre'), ('Ouro Preto', 'ouro preto'), ('Tiradentes', 'tiradentes'),
    ('Buenos Aires', 'buenos aires'), ('Santiago', 'santiago'), ('Bogotá', 'bogota'),
    ('Cidade do México', 'cidade do mexico|mexico city'), ('Toronto', 'toronto'),
    ('Vancouver', 'vancouver'), ('Montreal', 'montreal'), ('Singapura', 'singapura|singapore'),
    ('Hong Kong', 'hong kong'), ('Tóquio', 'toquio|tokyo'), ('Maldivas', 'maldivas|maldives'),
    ('Saint-Tropez', 'saint tropez|st tropez'), ('Courchevel', 'courchevel'),
    ('Forte de Marmi', 'forte de marmi'),
    ('Gstaad', 'gstaad'), ('Verbier', 'verbier'), ('Hamptons', 'hamptons'),
    ('Bal Harbour', 'bal harbour|bal harbor'), ('Fisher Island', 'fisher island'),
    ('Star Island', 'star island'), ('Brickell', 'brickell'),
]
ORGS = [
    ('Banco Central', r'banco central|\bbacen\b'),
    ('Banco Master', r'banco master'),
    ('STF', r'\bstf\b|supremo tribunal'),
    ('Polícia Federal', r'pol[ií]cia federal|\bpf\b'),
    ('Itaú', r'\bitau\b|\bitaú\b'),
    ('Fitch', r'\bfitch\b'),
    ('Brazil Journal', r'brazil journal'),
    ('Operação Compliance Zero', r'compliance zero'),
    ('Amex', r'\bamex\b|american express'),
]
# Names of tables he might actually say. Kept only when the word is in the text.
# Full phrases only. A single common word here would tag thousands of messages.
SEEDS = [
    'Fasano', 'Cipriani', 'Nobu', 'Zuma', 'Gero', 'Nusr-Et', 'Nusret', 'Puglia', 'Picci',
    'Carbone', 'Catch', 'Bagatelle', 'Novikov', 'Coya', 'Maní', 'Barbacoa', 'Rubaiyat',
    'Kosushi', 'Makoto', 'Kinoshita', 'Figueira', 'Coco Bambu', 'Fogo de Chão', 'Fogo de Chao',
    'Pobre Juan', 'D.O.M.', 'Garganta do Tigre', 'Rosewood', 'Setai', 'Faena', 'Fontainebleau',
    'Belmond', 'Copacabana Palace', 'Emiliano', 'Soho House', 'Surf Club', 'Delano', 'Four Seasons',
    'Cheval Blanc', 'Eden Rock', 'Contessa', 'La Petite Maison', 'Romazzino',
    'Da Paolino', 'Botanique', 'Shellona', 'Le Ti', 'Petite Plage', 'Gypsea', 'High Hill',
    'Breakers', 'La Guerite', 'Le Toiny', 'Venetian', 'Issa', 'Attimo', 'Parigi',
    'St Regis', 'Mandolin', 'Elcielo', 'Hotel das Girafas', 'One Hotel', 'Fasano Itaim',
    'Sexy Fish', 'Sugarfish', 'Sugar Fish', 'Casa Neos', 'Papi Steak', 'Ritz-Carlton',
    'Loulou', 'La Perouse', 'Costes', 'Maritaca', 'Transamerica', 'Sirene Beach',
    'Call Me Gabi', 'LPM', 'Amazonico', 'Starlight', 'Atlantis',
    'Six Senses', 'Cipriani', 'Langosteria', 'Pura Vida',
    'Casa Tua', 'Borgo Egnazia', 'Nihi', 'La Casita', 'Da Tonino', 'Les Pecheurs',
    "Chateau Zz's", "Zz's", 'Bill&co', 'Santa Marina', 'Komodo', 'Blue Mist',
    'Kantana', 'Sirenuse', "L'Atelier de Joel Robuchon", 'MILA Omakase', "L'Isola",
    'Mamo', 'Kimigawa', 'Casadonna', 'Tanit', 'Jondal', 'Planet Lodge', 'Aman',
    'Stadard',
]
SEED_KEYS = {norm(s) for s in SEEDS}
SEED_BY = {norm(s): s for s in SEEDS}
# Typed variants of a place already in SEEDS. The value is the name we show.
SEED_ALIAS = {
    'shelona': 'Shellona',
    'pula vida': 'Pura Vida',
}
# Observed sentence-scrap and weekday grabs. Not places.
BAD_NAME = set(map(norm, '''answer club surf salt seen spot shin fogo coco soho balada quinta sexta
segunda terca terça quarta domingo sabado sábado igreja paz tem dela dele ate até etc vou vai mesmo
ainda como outro outra nao não mas meus girafas obrigada obrigado entao então pega agora nosso
esperando floresta amigos sabia kkkkk tenho foi meu meio voce você sua pele detalhe organizar
familia família pacotinha final maximo máximo minimo mínimo julho italia itália orlando mia avra
relaxando almocou ultimo último eita ninguem ninguém market sauna amor niver ideia maravilhoso
vinho pensando dormindo principal entrar canto perto daqui aqui tambem também né ne lkkk haaha
due voce vai sentou foi outro dia tranquilo otima ótima ideia ninguem vai borda ela dentro
qual espaco espaço seu niver seus pais meus pais nao quero até segunda chama alguma seu nome
preferido agora desejo terminando voice nosso ate quarta os amigos esperando não sabia floresta
ou prefere abortar indo dormir kkkkk haahhaahahahaha simplificar cubano'''.split()))

PARTICLES = set('de da do das dos e em no na nos nas du la le di del the a o'.split())

def clean_piece(t):
    t = DET.sub('', t)
    t = re.sub(r'</?img>', '', t, flags=re.I)
    t = re.sub(r'<attached:[^>]*>', '[anexo]', t, flags=re.I)
    t = t.replace('[OCR figure text]', '')
    t = GREEK.sub('', t)
    # Keep ZWJ (U+200D) and variation selector 16 (U+FE0F). Stripping them
    # turns iPhone emoji sequences into broken text-style glyphs.
    t = re.sub(r'(?i)\[image\](?:\s*\[media\])?', '[imagem]', t)
    t = re.sub(r'(?i)\[audio\](?:\s*\[media\])?', '[áudio]', t)
    t = re.sub(r'(?i)\[video\](?:\s*\[media\])?', '[vídeo]', t)
    t = re.sub(r'(?i)\[document\](?:\s*\[REDACTED\]-?|\s*\[media\])?', '[documento]', t)
    t = re.sub(r'(?i)\[text\]', '[arquivo]', t)
    t = re.sub(r'(?i)\[imagem de visualização única[^\]]*\]', '[imagem]', t)
    t = re.sub(r'(?i)\[sticker\](?:\s*\[media\])?', '[figurinha]', t)
    t = re.sub(r'(?i)\[gif\](?:\s*\[media\])?', '[figurinha]', t)
    t = re.sub(r'(?i)\[contact\](?:\s*\[media\])?', '[contato]', t)
    t = re.sub(r'\[REDACTED\]-+', '[REDACTED]', t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    t = re.sub(r' *\n *', '\n', t)
    return t.strip()

def clean_report(t):
    t = clean_piece(t)
    kept = []
    for line in t.splitlines():
        if line.count('→') + line.count('←') > 12:
            continue
        if re.fullmatch(r'[\s|→←\-—._•]+', line or ''):
            continue
        kept.append(line)
    t = '\n'.join(kept)
    if is_forensic(t):
        return 'Horários de aplicativos. Identificadores omitidos.'
    t = re.sub(r'[ \t]*\|[ \t]*', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()

def is_forensic(t):
    low = (t or '').lower()
    stamps = len(re.findall(r'20\d{2}-\d{2}-\d{2}t\d{2}:\d{2}', low))
    if stamps >= 3 and ('whatsapp' in low or 'com.apple.' in low or 'mobilenotes' in low):
        return True
    if low.count('net.whatsapp') >= 2 or low.count('whatsapp:') >= 4 or low.count('net:whatsapp') >= 3:
        return True
    return False

def stamp(date, time):
    parts = (date or '').split('-')
    if len(parts) != 3 or not all(parts):
        return '[——:—— | ——]'
    _y, mo, d = parts
    hm = '——'
    if time and ':' in time:
        hh, mi = time.split(':')[:2]
        if hh.isdigit() and mi.isdigit():
            hm = f'{int(hh):02d}:{int(mi):02d}'
    return f'[{int(d):02d}:{int(mo):02d} | {hm}]'

def human_line_body(t):
    t = clean_piece(t or '')
    if is_forensic(t):
        t = 'Horários de aplicativos. Identificadores omitidos.'
    else:
        t = re.sub(r'(?i)\[(?:image|imagem)\](?:\s*\[media\])?', 'Foto', t)
        t = re.sub(r'(?i)\[(?:audio|áudio)\](?:\s*\[media\])?', 'Áudio', t)
        t = re.sub(r'(?i)\[(?:video|vídeo)\](?:\s*\[media\])?', 'Vídeo', t)
        t = re.sub(r'(?i)\[(?:document|documento)\](?:\s*\[REDACTED\]-?|\s*\[media\])?', 'Arquivo', t)
        t = re.sub(r'(?i)\[(?:text|arquivo|anexo)\]', 'Arquivo', t)
        t = re.sub(r'(?i)\[(?:sticker|gif|figurinha)\](?:\s*\[media\])?', 'Figurinha', t)
        t = re.sub(r'(?i)\[(?:contact|contato)\](?:\s*\[media\])?', 'Contato', t)
    t = redact(t)
    t = re.sub(r'(Foto|Áudio|Vídeo|Arquivo|Contato|Figurinha)(?:\s*\[REDACTED\])+', r'\1', t)
    t = re.sub(r'\s{2,}', ' ', t).strip()
    return t

# Job labels and place suffixes that NER saved onto contact cards.
ROLE = set(map(norm, '''motorista dermato baba babá ministro embaixador filho filha pai mae mãe
pais chef secretaria secretária massagista partner handler ceo stylist adv advogado arquiteto
financeiro mkt diretor conjur husband filipina nanny driver dr sr sra epf dpf pf bacen brb
'''.split()))

def canon_person_name(raw):
    name = re.sub(r'\s+', ' ', raw or '').strip()
    trail = re.compile(r'(?i)\s+(brasilia|mkt|financeiro\d*|motorista|brazil journal|conjur|banco master|diretor|financeiro|bacen|brb|banco|adv|arquiteto|epf|dpf|pf)$')
    prev = None
    while name and name != prev:
        prev = name
        name = trail.sub('', name).strip()
        name = re.sub(r'\s+\d+$', '', name).strip()
    toks = [t for t in name.split() if norm(t) not in ROLE and norm(t) not in {'brasilia', 'bacen', 'brb'}]
    if len(toks) >= 2 and norm(toks[-1]) == norm(toks[-2]):
        toks.pop()
    if not toks:
        return ''
    # A labeled card that collapses to one very common first name is not a person row.
    if len(toks) == 1 and norm(toks[0]) in {'daniel', 'alexandre', 'fabio', 'paulo', 'ana', 'maria', 'joao', 'jose'}:
        return ''
    name = ' '.join(toks)
    key = norm(name).replace('.', '')
    cities = {norm(c).replace('.', '') for c, _ in CITIES}
    if key in {'dv', 'vorcaro', 'daniel vorcaro', 'daniel bueno vorcaro', 'dani vorcaro', 'daniel bueno'}:
        return 'Daniel Vorcaro'
    if key in {'martha', 'martha graeff'}:
        return 'Martha Graeff'
    if key in {'alexandre de moraes', 'alexandre moraes'}:
        return 'Alexandre de Moraes'
    if not name or key in cities or key in {'st barths', 'saint barths', 'st barth'} or key in GENERIC or key in ROLE:
        return ''
    return name

def speaker(sender):
    return canon_person_name(sender) or (sender or '').strip()

def windows_of(msgs):
    docs, w = [], []
    def flush():
        if not w:
            return
        docs.append(w[:])
    for m in msgs:
        if w and (m['conv'] != w[-1]['conv'] or m['date'] != w[-1]['date']
                  or sec(m['time']) - sec(w[-1]['time']) > 900 or len(w) >= 8
                  or sum(len(x['text']) for x in w) > 600):
            flush(); w = []
        w.append(m)
    flush()
    return docs

def trim_name(raw):
    raw = re.sub(r'\s+', ' ', raw).strip(' .,;:!?-–—"\'“”()[]')
    toks = raw.split()
    while toks and (norm(toks[0]) in PARTICLES or norm(toks[0]) in GENERIC):
        toks.pop(0)
    while toks and (norm(toks[-1]) in PARTICLES or norm(toks[-1]) in GENERIC or norm(toks[-1]) in BAD_NAME or len(norm(toks[-1])) <= 2):
        toks.pop()
    if not toks:
        return ''
    if len(toks) > 4:
        return ''
    name = ' '.join(toks)
    if norm(name) in GENERIC or norm(name) in PARTICLES:
        return ''
    if all(norm(t) in GENERIC or norm(t) in PARTICLES for t in toks):
        return ''
    if re.fullmatch(r'[\d\W]+', name):
        return ''
    if len(norm(name)) < 3:
        return ''
    # sentence fragment: a lowercase Portuguese function word in the middle of a long grab
    if any(norm(t) in {'que', 'pra', 'pro', 'para', 'com', 'sem', 'uma', 'uns', 'por', 'porque', 'quando', 'onde'} for t in toks):
        return ''
    return name

STRONG = re.compile(r'(?i)\b(?:restaurante|trattoria|osteria|bistr[oô]|churrascaria|steakhouse|rod[ií]zio)\s+([A-Za-zÀ-ú][\w\'’.-]{1,}(?:\s+[A-Za-zÀ-ú][\w\'’.-]{1,}){0,3})')
PREP = re.compile(r'(?i)\b(?:jantar|almo[cç]ar|brunch|comer|reserv\w*|mesa|jantamos|almoc\w*)\s+(?:no|na|em|num|numa|pro|pra)\s+([A-Za-zÀ-ú][\w\'’.-]{2,}(?:\s+[A-Za-zÀ-ú][\w\'’.-]{2,}){0,3})')
WENT = re.compile(r'(?i)\b(?:passei|passamos|fui|fomos|estamos|estou|vou|vamos|cheguei|chego|t[oô]|to)\s+(?:no|na|em)\s+([A-Za-zÀ-ú][\w\'’.-]{3,}(?:\s+[A-Za-zÀ-ú][\w\'’.-]{2,}){0,2})')
HOTEL = re.compile(r'(?i)\b(?:hotel|resort|pousada)\s+([A-ZÀ-Ú][\w\'’.-]{2,}(?:\s+[A-ZÀ-Ú][\w\'’.-]{2,}){0,2})')
ATCAP = re.compile(r'(?i)\b(?:no|na|em)\s+([A-ZÀ-Ú][\w\'’.-]{2,}(?:\s+[A-ZÀ-Ú][\w\'’.-]{2,}){0,2})')

def load():
    msgs = json.load(open(os.path.join(SRC, 'messages.json')))
    chunks = json.load(open(os.path.join(SRC, 'report_chunks.json')))
    old = json.load(open(os.path.join(PUB, 'docs.json')))
    meta = json.load(open(os.path.join(PUB, 'meta.json')))
    ents = json.load(open(os.path.join(SRC, 'entities.json')))
    return msgs, chunks, old, meta, ents

def align(olds, wins, chunks):
    if len(olds) != len(wins) + len(chunks):
        return f'count {len(olds)} != {len(wins)} windows + {len(chunks)} chunks'
    for i, w in enumerate(wins):
        o = olds[i]
        if o['c'] != w[0]['conv'] or o['d'] != w[0]['date'] or o['t'] != w[0]['time'] or o['p'] != w[0]['page']:
            return f'window {i} {o["c"]} {o["d"]} {o["t"]} p{o["p"]} != {w[0]["conv"]} {w[0]["date"]} {w[0]["time"]} p{w[0]["page"]}'
        send = sorted({m['sender'] for m in w})
        if send != o['s']:
            return f'senders {i} {send} != {o["s"]}'
    return ''

def roster_of(msgs, ents):
    """Canonical people. First names are aliases only when they point at one person."""
    fixed = [
        ('Daniel Vorcaro', ['dv', 'daniel vorcaro', 'daniel bueno', 'daniel bueno vorcaro', 'dani vorcaro', 'vorcaro']),
        ('Martha Graeff', ['martha graeff', 'martha']),
    ]
    skip_ent = set(map(norm, 'jesus agradeço agradeço husband paizão paizao instagram st barths aston martin exmo kenya g entao tadinho coração tio dani david blair tony blair ben harper ben gorham ivanka'.split()))
    # conversation titles are reliable people, except the report and the self-chat
    titles = []
    for conv in sorted({m['conv'] for m in msgs}):
        if conv.startswith('IPJ') or conv.startswith('DV'):
            continue
        titles.append(conv)
    people = [{'name': n, 'aliases': set(a)} for n, a in fixed]
    def add_person(raw, extra=()):
        name = canon_person_name(raw)
        if not name or norm(name) in skip_ent:
            return
        aliases = {norm(name)}
        for a in extra:
            if a and not audit(a):
                aliases.add(norm(a))
        for p in people:
            if norm(p['name']) == norm(name):
                p['aliases'].update(aliases)
                return
        people.append({'name': name, 'aliases': aliases})
    for title in titles:
        add_person(title, [title])
    for e in ents:
        if e['label'] != 'PER' or e['count'] < 8:
            continue
        n = e['name'].strip()
        if norm(n) in skip_ent or norm(n) in GENERIC or audit(n):
            continue
        if len(n.split()) == 1 and len(n) < 4:
            continue
        add_person(n)
    # unique first names become aliases
    firsts = defaultdict(list)
    for p in people:
        f = norm(p['name'].split()[0])
        if f not in {'dv', 'daniel'} and f not in ROLE and f not in GENERIC and len(f) >= 4:
            firsts[f].append(p)
    for f, ps in firsts.items():
        if len(ps) == 1:
            ps[0]['aliases'].add(f)
    return people

def compile_people(people):
    # longest alias first
    items = []
    for i, p in enumerate(people):
        for a in p['aliases']:
            if len(a) < 3:
                continue
            items.append((a, i))
    items.sort(key=lambda x: -len(x[0]))
    return items

def find_people(text, compiled):
    n = norm(text)
    found = []
    seen = set()
    occupied = []
    for a, i in compiled:
        if i in seen or len(a) < 3:
            continue
        m = re.search(r'(?<!\w)' + re.escape(a) + r'(?!\w)', n)
        if not m:
            continue
        span = m.span()
        if any(span[0] < b and span[1] > a0 for a0, b in occupied):
            continue
        occupied.append(span)
        seen.add(i)
        found.append(i)
    return found

def find_list(text, rows):
    n = norm(text)
    hit = []
    for name, pat in rows:
        if name == 'Roma':
            if re.search(r'(?<![\w])(?:Roma|Rome)(?!\w)', text) or re.search(r'(?i)(?:\b(?:em|para|pra|pro|no|na|in|to|from|de)\s+)(?:roma|rome)\b', text):
                hit.append(name)
            continue
        if name == 'Nice':
            if re.search(r'(?<![\w])Nice(?!\w)', text) or re.search(r'(?i)(?:\b(?:em|para|pra|pro|no|na|in|to|from)\s+)nice\b', text):
                hit.append(name)
            continue
        wrapped = pat if ('\\b' in pat or '(?<!' in pat) else rf'(?<!\w)(?:{pat})(?!\w)'
        if re.search(wrapped, n):
            hit.append(name)
    if 'Rio de Janeiro' in hit and 'Rio' in hit:
        hit.remove('Rio')
    return hit

def find_seeds(text, seeds):
    n = norm(text)
    hit = []
    seen = set()
    pairs = [(s, s) for s in seeds] + list(SEED_ALIAS.items())
    for raw, display in pairs:
        sn, key = norm(raw), norm(display)
        if key in seen or len(sn) < 3:
            continue
        if re.search(r'(?<!\w)' + re.escape(sn) + r'(?!\w)', n):
            seen.add(key)
            hit.append(display)
    return hit

def surface(counter):
    return counter.most_common(1)[0][0]

def build():
    msgs, chunks, old, meta, ents = load()
    wins = windows_of(msgs)
    err = align(old, wins, chunks)
    people = roster_of(msgs, ents)
    compiled = compile_people(people)
    # pass 1: candidate venue strings
    cand = Counter()
    surfaces = defaultdict(Counter)
    occurrences = defaultdict(list)  # key -> list of (doc_i, cue)
    food_docs = set()
    travel_docs = set()
    # precompute cleaned window text (redacted) aligned with old docs
    shown = []
    food_flag = []
    travel_flag = []
    for wi, w in enumerate(wins):
        parts = []
        food = False
        travel = False
        raw_join = []
        for m in w:
            c = human_line_body(m['text'])
            if not c:
                continue
            parts.append(f"{stamp(m['date'], m['time'])} {speaker(m['sender'])}: {c}")
            raw_join.append(c)
            if FOOD_RE.search(m['text']) or FOOD_RE.search(c):
                food = True
            if TRAVEL_RE.search(m['text']) or TRAVEL_RE.search(c):
                travel = True
        blob = '\n'.join(raw_join)
        shown.append('\n'.join(parts) if parts else redact(clean_piece(w[0]['text'])))
        food_flag.append(food)
        travel_flag.append(travel)
        if food:
            food_docs.add(wi)
        if travel:
            travel_docs.add(wi)
        cues = []
        for rx, cue in ((STRONG, 'strong'), (PREP, 'prep'), (HOTEL, 'hotel'), (ATCAP, 'cap'), (WENT, 'went')):
            if cue in {'cap', 'went'} and not food:
                continue
            for m in rx.finditer(blob):
                name = trim_name(m.group(1))
                if not name:
                    continue
                if any(norm(name) == norm(p['name']) or norm(name) in p['aliases'] for p in people):
                    continue
                k = norm(name)
                cand[k] += 1
                surfaces[k][name] += 1
                cues.append((k, cue))
        for s in find_seeds(blob, SEEDS):
            k = norm(s)
            cand[k] += 1
            surfaces[k][s] += 1
            cues.append((k, 'seed'))
        for k, cue in cues:
            occurrences[k].append((wi, cue))
    def proper_name(k):
        if k in {'restaurant', 'and', 'hotel', 'restaurante'}:
            return False
        if k in SEED_KEYS:
            return True
        if k in BAD_NAME or k in GENERIC or len(k) < 3:
            return False
        toks = k.split()
        if not toks or len(toks) > 3:
            return False
        if len(toks) == 1 and len(toks[0]) < 5:
            return False
        if len(toks) >= 3:
            return False
        if any(t in BAD_NAME or t in GENERIC or t in PARTICLES for t in toks):
            return False
        surf = surface(surfaces[k])
        parts = [p for p in surf.split() if norm(p) not in PARTICLES]
        # A real sign has a capital on each word, or it is one of the curated names.
        if k in SEED_KEYS:
            return True
        return bool(parts) and all(p[:1].isupper() for p in parts)
    keep = {}
    for k, n in cand.items():
        cues = {c for _, c in occurrences[k]}
        if not proper_name(k):
            continue
        if 'seed' in cues or (cues & {'strong', 'prep', 'hotel'}):
            keep[k] = SEED_BY.get(k) or surface(surfaces[k])
    # report text
    report_shown = []
    for c in chunks:
        report_shown.append(redact(clean_report(c['text'])))
    # concept masks for centroids, filled after we know places/orgs/venues per doc
    ven_of = defaultdict(set)
    plc_of = defaultdict(set)
    org_of = defaultdict(set)
    who_of = defaultdict(set)
    for wi, w in enumerate(wins):
        blob = shown[wi]
        for k, name in keep.items():
            if re.search(r'(?<!\w)' + re.escape(k) + r'(?!\w)', norm(blob)):
                # classify
                if any(norm(name) == norm(city) for city, _ in CITIES):
                    plc_of[wi].add(name)
                else:
                    ven_of[wi].add(name)
        for city in find_list(blob, CITIES):
            plc_of[wi].add(city)
        for org in find_list(blob, ORGS):
            org_of[wi].add(org)
        for pi in find_people(blob, compiled):
            who_of[wi].add(people[pi]['name'])
        for m in w:
            if m['sender'] == 'DV':
                who_of[wi].add('Daniel Vorcaro')
            else:
                sn = norm(m['sender'])
                hit = None
                for p in people:
                    if sn == norm(p['name']) or sn in p['aliases']:
                        hit = p['name']; break
                who_of[wi].add(hit or m['sender'])
    rep_who, rep_plc, rep_org = defaultdict(set), defaultdict(set), defaultdict(set)
    for ci, text in enumerate(report_shown):
        if text.startswith('Tabela de metadados'):
            rep_who[ci].add('Polícia Federal')
            continue
        for city in find_list(text, CITIES):
            rep_plc[ci].add(city)
        for org in find_list(text, ORGS):
            rep_org[ci].add(org)
        for pi in find_people(text, compiled):
            rep_who[ci].add(people[pi]['name'])
        rep_who[ci].add('Polícia Federal')
    # Published docs drop windows whose redacted text is empty. Match in order.
    win_to_pub = [None] * len(wins)
    wi = 0
    unmatched = []
    report_at = next((i for i, o in enumerate(old) if o['c'].startswith('IPJ')), len(old))
    for di, o in enumerate(old[:report_at]):
        guard = 0
        found = False
        while wi < len(wins) and guard < 12:
            w = wins[wi]
            same = (o['c'] == w[0]['conv'] and o['d'] == w[0]['date'] and o['t'] == w[0]['time']
                    and o['p'] == w[0]['page'] and sorted({m['sender'] for m in w}) == o['s'])
            if same:
                win_to_pub[wi] = di
                wi += 1
                found = True
                break
            wi += 1
            guard += 1
        if not found:
            unmatched.append(di)
    chunk_to_pub = [None] * len(chunks)
    if len(old) - report_at == len(chunks) and all(old[report_at + i]['p'] == chunks[i]['page'] for i in range(len(chunks))):
        for i in range(len(chunks)):
            chunk_to_pub[i] = report_at + i
    else:
        unmatched.append('report-pages')
    def rekey(src, mapper):
        out = defaultdict(set)
        for i, names in src.items():
            j = mapper[i] if i < len(mapper) else None
            if j is None:
                continue
            out[j] |= set(names)
        return out
    def drop_short(map_of):
        for i, names in list(map_of.items()):
            keys = [norm(n) for n in names]
            drop = {n for n in names if any(norm(n) != o and norm(n) in o for o in keys)}
            map_of[i] -= drop
    drop_short(ven_of)
    ven_of = rekey(ven_of, win_to_pub)
    plc_of = rekey(plc_of, win_to_pub)
    org_of = rekey(org_of, win_to_pub)
    who_of = rekey(who_of, win_to_pub)
    for ci, names in rep_who.items():
        j = chunk_to_pub[ci]
        if j is not None:
            who_of[j] |= names
    for ci, names in rep_plc.items():
        j = chunk_to_pub[ci]
        if j is not None:
            plc_of[j] |= names
    for ci, names in rep_org.items():
        j = chunk_to_pub[ci]
        if j is not None:
            org_of[j] |= names
    food_docs = {win_to_pub[i] for i in food_docs if win_to_pub[i] is not None}
    travel_docs = {win_to_pub[i] for i in travel_docs if win_to_pub[i] is not None}
    text_of = {}
    for i, t in enumerate(shown):
        j = win_to_pub[i]
        if j is not None:
            text_of[j] = t
    for i, t in enumerate(report_shown):
        j = chunk_to_pub[i]
        if j is None:
            continue
        body = t
        if is_forensic(body) or body.startswith('Tabela de metadados') or body.startswith('Horários de aplicativos'):
            body = 'Horários de aplicativos. Identificadores omitidos.'
        text_of[j] = f"{stamp(old[j].get('d') or '', old[j].get('t') or '')} Polícia Federal: {body}"
    err = 'ok' if not unmatched else f'unmatched {unmatched[:8]}'
    # centroids from existing int8 vectors
    import numpy as np
    E = np.fromfile(os.path.join(PUB, 'doc_emb.i8'), dtype=np.int8).reshape(len(old), meta['dim']).astype(np.float32)
    E *= meta['doc_scale'] / 127.0
    def centroid(idxs):
        if not idxs:
            return None
        v = E[list(idxs)].mean(0)
        nrm = np.linalg.norm(v)
        if nrm == 0:
            return None
        return [round(float(x), 5) for x in (v / nrm)]
    place_idx = [i for i in range(len(old)) if plc_of[i]]
    org_idx = [i for i in range(len(old)) if org_of[i]]
    ven_idx = [i for i in range(len(old)) if ven_of[i]]
    concepts = {
        'dining': centroid(food_docs),
        'travel': centroid(travel_docs),
        'place': centroid(place_idx),
        'org': centroid(org_idx),
        'venue': centroid(ven_idx),
    }
    # catalog: one card per venue/place/org, evidence = doc indexes (client ranks them)
    def catalog(map_of, kind):
        acc = defaultdict(lambda: {'name': '', 'kind': kind, 'docs': []})
        for i, names in map_of.items():
            for name in names:
                k = norm(name)
                acc[k]['name'] = name
                acc[k]['docs'].append(i)
        rows = []
        for k, v in acc.items():
            v['docs'] = sorted(set(v['docs']))
            if kind == 'venue' and len(v['docs']) < 1:
                continue
            rows.append(v)
        rows.sort(key=lambda r: -len(r['docs']))
        return rows
    facets = {
        'venues': catalog(ven_of, 'venue'),
        'places': catalog(plc_of, 'place'),
        'orgs': catalog(org_of, 'org'),
    }
    # person → conversations
    convs_of = defaultdict(set)
    for i, names in who_of.items():
        for n in names:
            convs_of[n].add(old[i]['c'])
    roster_out = []
    for p in people:
        roster_out.append({
            'name': p['name'],
            'aliases': sorted(p['aliases']),
            'convs': sorted(convs_of.get(p['name'], [])),
        })
    # publishable docs: same objects, cleaned text, extra fields
    out_docs = []
    for i, o in enumerate(old):
        text = text_of.get(i)
        if not text:
            body = human_line_body(o.get('x') or '')
            who = 'Polícia Federal' if str(o.get('c', '')).startswith('IPJ') else speaker((o.get('s') or ['?'])[0])
            text = f"{stamp(o.get('d') or '', o.get('t') or '')} {who}: {body}" if body else (o.get('x') or '')
        d = dict(o)
        d['x'] = text
        d['who'] = sorted(who_of[i])
        d['ven'] = sorted(ven_of[i])
        d['plc'] = sorted(plc_of[i])
        d['org'] = sorted(org_of[i])
        d['food'] = 1 if i in food_docs else 0
        d['trip'] = 1 if i in travel_docs else 0
        out_docs.append(d)
    review = {
        'align': err or 'ok',
        'matched_windows': sum(j is not None for j in win_to_pub),
        'windows': len(wins),
        'chunks': len(chunks),
        'venues_kept': len(keep),
        'food_windows': len(food_docs),
        'travel_windows': len(travel_docs),
        'top_venues': sorted(({'name': keep[k], 'n': len({i for i, _ in occurrences[k]})} for k in keep), key=lambda r: -r['n'])[:80],
        'dropped_once': [surface(surfaces[k]) for k, n in cand.most_common() if k not in keep][:40],
    }
    return out_docs, facets, roster_out, concepts, meta, review

def _scrub_name(s):
    t = redact(s)
    return '' if t == '[REDACTED]' or '[REDACTED]' in t else t

def publish(out_docs, facets, roster, concepts, meta):
    os.makedirs(PUB, exist_ok=True)
    for d in out_docs:
        d['x'] = redact(d['x'])
        for k in ('who', 'ven', 'plc', 'org'):
            d[k] = [n for n in (_scrub_name(x) for x in d[k]) if n]
    for kind in ('venues', 'places', 'orgs'):
        kept=[]
        for row in facets[kind]:
            row['name'] = _scrub_name(row['name'])
            if row['name']:
                kept.append(row)
        facets[kind] = kept
    kept_people=[]
    for p in roster:
        name=_scrub_name(p['name'])
        if not name:
            continue
        p['name']=name
        p['aliases']=[a for a in p['aliases'] if a and not audit(a)]
        kept_people.append(p)
    roster=kept_people
    blob = json.dumps({'docs': out_docs, 'facets': facets, 'roster': roster}, ensure_ascii=False)
    hits = audit(blob)
    if hits:
        raise SystemExit('redaction audit failed: ' + json.dumps(hits))
    json.dump(out_docs, open(os.path.join(PUB, 'docs.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump({'venues': facets['venues'], 'places': facets['places'], 'orgs': facets['orgs'], 'people': roster},
              open(os.path.join(PUB, 'facets.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    meta = dict(meta)
    meta['concepts'] = {k: v for k, v in concepts.items() if v}
    meta['lex_bonus'] = 0
    json.dump(meta, open(os.path.join(PUB, 'meta.json'), 'w'), indent=1)
    # second pass: the publisher's own audit script, over the data dir
    bad = {}
    for fn in ('docs.json', 'facets.json', 'meta.json', 'keywords.json'):
        p = os.path.join(PUB, fn)
        if os.path.exists(p):
            h = audit(open(p, encoding='utf-8').read())
            if h:
                bad[fn] = h
    if bad:
        raise SystemExit('audit after write failed: ' + json.dumps(bad))

def main():
    out_docs, facets, roster, concepts, meta, review = build()
    os.makedirs(BUILD, exist_ok=True)
    json.dump(review, open(os.path.join(BUILD, 'review.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({k: review[k] for k in review if k != 'top_venues'}, ensure_ascii=False, indent=1))
    print('TOP')
    for r in review['top_venues']:
        print(f"{r['n']:4} {r['name']}")
    print('concepts', {k: bool(v) for k, v in concepts.items()})
    if '--publish' in sys.argv:
        if review['align'] != 'ok':
            raise SystemExit('not publishing, alignment: ' + review['align'])
        publish(out_docs, facets, roster, concepts, meta)
        print('published', len(out_docs), 'venues', len(facets['venues']), 'places', len(facets['places']), 'orgs', len(facets['orgs']))

if __name__ == '__main__':
    main()
