from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
import re, sys, collections, json
txt=open(sys.argv[1],encoding='utf-8').read()
pat=re.compile(r'^\u200e?\[(\d{4}-\d{2}-\d{2}), ([^\]]+)\] (.*?): ', re.M)
ms=list(pat.finditer(txt))
msgs=[]
for i,m in enumerate(ms):
    end=ms[i+1].start() if i+1<len(ms) else len(txt)
    body=txt[m.end():end].strip()
    msgs.append((m.group(1),m.group(3).replace('‪','').replace('‬',''),body))
system=[x for x in msgs if x[1]=='Berlin RevOps Chapter' or x[2].startswith('‎') and re.search(r'joined|added|left|removed|created|changed|deleted|pinned|encrypted|invite|now an admin',x[2]) and len(x[2])<200]
user=[x for x in msgs if x not in system]
print('total entries',len(msgs),'system',len(system),'user',len(user))
c=collections.Counter(x[1] for x in user)
print(c.most_common(10))
print('Alexandre',c['Alexandre'])
print('first',msgs[0][0],'last',msgs[-1][0],'participants',len(c))
media=[x for x in user if re.search(r'omitted|This message was deleted',x[2])]
print('media/deleted',len(media))
for x in system[:0]: print(x)
print(collections.Counter(re.sub(r'[^a-z ]','',x[2].lower())[:30] for x in system).most_common(15))
