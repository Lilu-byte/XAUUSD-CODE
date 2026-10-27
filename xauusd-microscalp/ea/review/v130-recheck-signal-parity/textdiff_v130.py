"""Compare the text of every function shared by the EA and the indicator (comments and whitespace ignored).
Run: python3 -I textdiff_v130.py"""
import re, difflib
EA = open('/mnt/project-files/xauusd-microscalp/ea/GoldMicroScalp.mq5').read()
IN = open('/mnt/project-files/xauusd-microscalp/ea/GoldMicroScalpSignals.mq5').read()
NAMES = ['SigPullback', 'SigSpikeFade', 'SigQuarterFade', 'SessionVWAP', 'DetectPatterns', 'CPVote', 'InSession', 'M5Dir',
         'ParseTod', 'PBody', 'PUp', 'PLo', 'PBull', 'PBear']


def func(src, name):
    m = re.search(r'^[A-Za-z_][\w ]*\b' + name + r'\s*\(', src, re.M)
    if not m: return None
    i = src.index('{', m.end()); d = 0
    for j in range(i, len(src)):
        d += src[j] == '{'; d -= src[j] == '}'
        if d == 0: return src[m.start():j + 1]


def norm(s):
    s = re.sub(r'//[^\n]*', '', s)
    return [re.sub(r'\s+', ' ', l).strip() for l in s.split('\n') if l.strip()]


for n in NAMES:
    a, b = func(EA, n), func(IN, n)
    if a is None or b is None:
        print(f'{n}: missing in', 'EA' if a is None else 'indicator'); continue
    na, nb = norm(a), norm(b)
    print(f'{n:15s}', 'IDENTICAL' if na == nb else 'DIFFERENT', f'({len(na)} lines)')
    if na != nb:
        for l in difflib.unified_diff(na, nb, 'EA', 'indicator', lineterm='', n=0): print('   ', l)
# shared globals / tables
for pat in (r'string PatShort\[NPAT\][^;]*;', r'int\s+PatDir\[NPAT\][^;]*;', r'#define NPAT \d+', r'#define MOD_\w+ \d+',
            r'cpOn\[\d+\]\s*=\s*\w+;'):
    A = [re.sub(r'\s+', ' ', x) for x in re.findall(pat, EA)]; B = [re.sub(r'\s+', ' ', x) for x in re.findall(pat, IN)]
    print(f'{pat:32s}', 'IDENTICAL' if A == B else f'DIFFERENT\n   EA {A}\n   IN {B}', f'({len(A)} items)')
# enum and the inputs both files declare: same defaults?
def inputs(src):
    return {m.group(2): m.group(3).strip() for m in re.finditer(r'^input\s+(\w+)\s+(\w+)\s*=\s*([^;]+);', src, re.M)}
ie, ii = inputs(EA), inputs(IN)
print('inputs in both with different defaults:', {k: (ie[k], ii[k]) for k in ie.keys() & ii.keys() if ie[k] != ii[k]})
print('EA signal/filter inputs the indicator lacks:', sorted(k for k in ie.keys() - ii.keys()))
print('enum identical:', re.search(r'enum ENUM_M5_ALIGN\s*\{[^}]*\}', EA).group(0).split() == re.search(r'enum ENUM_M5_ALIGN\s*\{[^}]*\}', IN).group(0).split())
