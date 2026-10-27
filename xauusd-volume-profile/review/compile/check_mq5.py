"""Static checks for an MQL5 source: encoding, brace/paren/bracket balance,
StringFormat specifier vs argument counts, called identifiers."""
import re, sys

path = sys.argv[1]
raw = open(path, 'rb').read()
print("bytes:", len(raw), "BOM:", raw[:3] == b'\xef\xbb\xbf', "CRLF:", b'\r\n' in raw)
nonascii = [(i, b) for i, b in enumerate(raw) if b > 127]
print("non-ASCII bytes:", len(nonascii))
tabs = raw.count(b'\t')
print("tabs:", tabs)
src = raw.decode('utf-8')

# strip comments and strings, keep line structure
out = []
i = 0; n = len(src); strings = []
while i < n:
    c = src[i]
    if src.startswith('//', i):
        j = src.find('\n', i); j = n if j < 0 else j
        out.append(' ' * (j - i)); i = j
    elif src.startswith('/*', i):
        j = src.find('*/', i) + 2
        out.append(''.join(ch if ch == '\n' else ' ' for ch in src[i:j])); i = j
    elif c == '"':
        j = i + 1
        while src[j] != '"':
            if src[j] == '\\': j += 1
            if src[j] == '\n': print("unterminated string at line", src.count('\n', 0, i) + 1)
            j += 1
        strings.append((src.count('\n', 0, i) + 1, src[i + 1:j]))
        out.append('"' + 'S' * (j - i - 1) + '"'); i = j + 1
    elif c == "'":
        j = src.find("'", i + 1)
        out.append("'" + 'C' * (j - i - 1) + "'"); i = j + 1
    else:
        out.append(c); i += 1
code = ''.join(out)
assert len(code) == len(src)

pairs = {')': '(', ']': '[', '}': '{'}
stack = []
ok = True
for idx, ch in enumerate(code):
    if ch in '([{':
        stack.append((ch, idx))
    elif ch in ')]}':
        if not stack or stack[-1][0] != pairs[ch]:
            print("mismatch", ch, "at line", code.count('\n', 0, idx) + 1); ok = False; break
        stack.pop()
if stack:
    ok = False
    for ch, idx in stack: print("unclosed", ch, "line", code.count('\n', 0, idx) + 1)
print("balance ok:", ok)
for ch in '(){}[]':
    print(ch, code.count(ch), end='  ')
print()

# StringFormat / PrintFormat checks
def split_args(s):
    args, depth, cur = [], 0, ''
    for ch in s:
        if ch in '([{': depth += 1
        if ch in ')]}': depth -= 1
        if ch == ',' and depth == 0:
            args.append(cur); cur = ''
        else:
            cur += ch
    args.append(cur)
    return args

for m in re.finditer(r'\b(StringFormat|PrintFormat)\s*\(', code):
    start = m.end(); depth = 1; j = start
    while depth:
        if code[j] == '(': depth += 1
        elif code[j] == ')': depth -= 1
        j += 1
    inner_src = src[start:j - 1]
    inner_code = code[start:j - 1]
    args = split_args(inner_code)
    # recover format text from original source
    fmt_code = args[0]
    off = inner_code.find(fmt_code)
    fmt = src[start + off:start + off + len(fmt_code)].strip().strip('"')
    specs = re.findall(r'%(?:%|[-+ #0]*\d*(?:\.\d+)?(?:h|l|ll|I64|I32)?[diouxXeEfgGcCsS])', fmt)
    real = [s for s in specs if s != '%%']
    line = code.count('\n', 0, m.start()) + 1
    print(f"line {line}: {m.group(1)} specs={real} args={len(args) - 1}",
          "OK" if len(real) == len(args) - 1 else "MISMATCH")
    for a in args[1:]:
        k = inner_code.find(a)
        print("    arg:", src[start + k:start + k + len(a)].strip()[:90])

# identifiers used as calls
calls = {}
for m in re.finditer(r'\b([A-Za-z_]\w*)\s*\(', code):
    name = m.group(1)
    calls.setdefault(name, []).append(code.count('\n', 0, m.start()) + 1)
defs = set(re.findall(r'^\s*(?:[A-Za-z_]\w*\s+)+([A-Za-z_]\w*)\s*\([^;]*\)\s*$', code, re.M))
print("defined functions:", sorted(defs))
kw = {'if', 'for', 'while', 'return', 'switch', 'sizeof'}
print("called (not defined here):")
for k in sorted(calls):
    if k not in defs and k not in kw:
        print("  ", k, calls[k][:12])
print("user functions: first call vs definition line")
for d in sorted(defs):
    dl = [i + 1 for i, l in enumerate(code.split('\n')) if re.match(r'^\s*(?:[A-Za-z_]\w*\s+)+' + d + r'\s*\(', l)]
    print("  ", d, "defined", dl, "called", [c for c in calls.get(d, []) if c not in dl])
