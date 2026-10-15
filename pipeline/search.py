#!/usr/bin/env python
import sys, argparse, textwrap
from engine import Engine
a=argparse.ArgumentParser(); a.add_argument('query'); a.add_argument('-t','--threshold',type=float,default=90); a.add_argument('-n','--limit',type=int,default=15); a.add_argument('--cpu',action='store_true')
o=a.parse_args(); e=Engine('cpu' if o.cpu else None); r=e.search(o.query,o.threshold,o.limit)
print(f"Query: {o.query!r} — {r['n_above']} windows/chunks >= {o.threshold:.0f}%\n")
for h in r['results']:
    print(f"{h['pct']:5.1f}%  [{h['conv']}] {h['date']} {h['time']} p.{h['page']}  {', '.join(h['senders'])}")
    print(textwrap.indent(textwrap.shorten(h['text'].replace('\n',' / '),300),'        '))
print('\nRelated keywords:',', '.join(f"{k['keyword']} ({k['pct']:.0f}%)" for k in r['related_keywords'][:15]))
