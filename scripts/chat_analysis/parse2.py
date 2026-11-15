from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
import re, sys, collections
txt=open(sys.argv[1],encoding='utf-8').read()
groups=set(sys.argv[2:])
pat=re.compile(r'^‎?\[(\d{4}-\d{2}-\d{2}), ([^\]]+)\] (.*?): ', re.M)
ms=list(pat.finditer(txt)); msgs=[]
for i,m in enumerate(ms):
    end=ms[i+1].start() if i+1<len(ms) else len(txt)
    msgs.append((m.group(1),m.group(3).replace('‪','').replace('‬','').replace(' ',' '),txt[m.end():end].strip()))
kw=r'joined|added|left|removed|created|changed|deleted|pinned|encrypted|invite|admin|Welcome to the group'
def sysm(x): return x[1] in groups or (x[2].startswith('‎') and re.search(kw,x[2]) and len(x[2])<200)
sy=[x for x in msgs if sysm(x)]; us=[x for x in msgs if not sysm(x)]
c=collections.Counter(x[1] for x in us)
print('total',len(msgs),'system',len(sy),'user',len(us),'participants',len(c))
print(c.most_common(8)); print('Alexandre',c['Alexandre'], 'rank', sorted(c.values(),reverse=True).index(c['Alexandre'])+1)
print('first',msgs[0][0],'last',msgs[-1][0])
# sanity: system items that are long or not obviously system
for x in sy:
    if not re.search(kw,x[2]): print('CHECK',x)
