"""Compare named MQL5 functions between the EA and the indicator, ignoring comments and whitespace."""
import re, sys
EA = '/mnt/project-files/xauusd-microscalp/ea/GoldMicroScalp.mq5'
IND = '/mnt/project-files/xauusd-microscalp/ea/GoldMicroScalpSignals.mq5'

def strip(src):
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith('//', i):
            j = src.find('\n', i); i = n if j < 0 else j
        elif src.startswith('/*', i):
            j = src.find('*/', i + 2); i = n if j < 0 else j + 2
        elif src[i] == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == '\\' else 1
            out.append(src[i:j + 1]); i = j + 1
        else:
            out.append(src[i]); i += 1
    return ''.join(out)

def func(src, name):
    m = re.search(r'\b[\w]+\s+' + name + r'\s*\(', src)
    if not m: return None
    i = src.index('{', m.end()); d = 0
    for j in range(i, len(src)):
        if src[j] == '{': d += 1
        elif src[j] == '}':
            d -= 1
            if d == 0: return src[m.start():j + 1]

ea, ind = strip(open(EA).read()), strip(open(IND).read())
names = sys.argv[1:] or ['M5Dir', 'InSession', 'CPVote', 'SigPullback', 'SigSpikeFade', 'SigQuarterFade',
                          'SessionVWAP', 'DetectPatterns', 'ParseTod', 'PBody', 'PUp', 'PLo', 'PBull', 'PBear']
for nm in names:
    a, b = func(ea, nm), func(ind, nm)
    if a is None or b is None:
        print(f'{nm:15s} MISSING ea={a is not None} ind={b is not None}'); continue
    na, nb = re.sub(r'\s+', '', a), re.sub(r'\s+', '', b)
    print(f'{nm:15s} {"IDENTICAL" if na == nb else "DIFFERENT"}  ({len(na)} chars)')
    if na != nb:
        import difflib
        for l in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm=''): print('   ', l)
# array / define tables that the shared functions read
for pat in [r'string\s+PatShort\[NPAT\][^;]*;', r'int\s+PatDir\[NPAT\][^;]*;', r'#define\s+NPAT\s+\d+', r'#define\s+MOD_\w+\s+\d+',
            r'#define\s+NMOD\s+\d+', r'enum\s+ENUM_M5_ALIGN\s*\{[^}]*\}', r'cpOn\[\d+\]\s*=\s*\w+;']:
    a = [re.sub(r'\s+', '', x) for x in re.findall(pat, ea)]; b = [re.sub(r'\s+', '', x) for x in re.findall(pat, ind)]
    print(f'{pat[:28]:30s} {"IDENTICAL" if a == b else "DIFFERENT"} ({len(a)} vs {len(b)})')
