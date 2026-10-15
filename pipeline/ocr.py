import signal
import os, sys, time, json, glob, torch, fitz, shutil
from transformers import AutoModel, AutoTokenizer
M='baidu/Unlimited-OCR'
pages=[int(x) for x in sys.argv[1].split(',')] if ',' in sys.argv[1] else list(range(int(sys.argv[1]),int(sys.argv[2])+1))
os.makedirs('ocr',exist_ok=True); os.makedirs('img',exist_ok=True)
tok=AutoTokenizer.from_pretrained(M,trust_remote_code=True)
model=AutoModel.from_pretrained(M,trust_remote_code=True,use_safetensors=True,torch_dtype=torch.bfloat16).eval().cuda()
doc=fitz.open('../vorcaro.pdf')
for p in pages:
    out=f'ocr/p{p:04d}.md'
    if os.path.exists(out): continue
    img=f'img/p{p:04d}.png'
    doc[p-1].get_pixmap(matrix=fitz.Matrix(200/72,200/72)).save(img)
    od=f'tmp_ocr/{p}'; os.makedirs(od,exist_ok=True)
    t=time.time()
    class TO(Exception): pass
    def h(*a): raise TO()
    signal.signal(signal.SIGALRM,h); signal.alarm(150)
    try:
      r=model.infer(tok,prompt='<image>document parsing.',image_file=img,output_path=od,base_size=1024,image_size=640,crop_mode=True,max_length=3072,no_repeat_ngram_size=35,ngram_window=128,save_results=True)
    except TO:
      print(json.dumps({'page':p,'timeout':True}),flush=True); open(out,'w').write(''); torch.cuda.empty_cache(); continue
    finally: signal.alarm(0)
    dt=time.time()-t
    mm=glob.glob(od+'/*.mmd')+glob.glob(od+'/*.md')
    txt=open(mm[0]).read() if mm else (r if isinstance(r,str) else '')
    open(out,'w').write(txt)
    print(json.dumps({'page':p,'sec':round(dt,1),'chars':len(txt)}),flush=True)
