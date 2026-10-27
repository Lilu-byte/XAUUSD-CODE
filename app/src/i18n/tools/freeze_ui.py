# en/ui_[abc].tsv (index -> English, numbered as in tools/ui_keys.tsv) -> en/ui_en.json (Persian key -> English)
import json,glob,re,os
D='/tmp/claude-0/-home-user/a290f82c-6216-50d1-bfba-3e81a0d181bc/scratchpad/'
keys={}
for ln in open(D+'tools/ui_keys.tsv',encoding='utf8'):
    i,line,k,ctx=ln.rstrip('\n').split('\t',3); keys[int(i)]=json.loads(k)
en={}
for f in sorted(glob.glob(D+'en/ui_[abc].tsv')):
    for ln in open(f,encoding='utf8'):
        if not ln.strip(): continue
        i,e=ln.rstrip('\n').split('\t',1); en[int(i)]=e
miss=[i for i in keys if i not in en]; extra=[i for i in en if i not in keys]
assert not miss and not extra,(miss[:10],extra[:10])
out={}
for i,k in keys.items():
    e=en[i]
    # placeholders must match
    a=sorted(set(re.findall(r'\{(\d)\}',k))); b=sorted(set(re.findall(r'\{(\d)[}|]',e)))
    assert a==b,(i,k,e)
    out[k]=e
path=D+'en/ui_en.json'
old=json.load(open(path,encoding='utf8')) if os.path.exists(path) else {}
old.update(out)
json.dump(old,open(path,'w',encoding='utf8'),ensure_ascii=False,indent=0)
print(len(old))
