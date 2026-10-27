"""Brace/paren balance after stripping comments and strings; StringFormat/PrintFormat specifier vs argument count."""
import re, sys
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/ea/review/v130-recheck-compile-logic')
FILES = ['/mnt/project-files/xauusd-microscalp/ea/GoldMicroScalp.mq5', '/mnt/project-files/xauusd-microscalp/ea/GoldMicroScalpSignals.mq5']

def strip(src, keep_strings):
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith('//', i):
            j = src.find('\n', i); i = n if j < 0 else j
        elif src.startswith('/*', i):
            j = src.find('*/', i + 2); i = n if j < 0 else j + 2
        elif src[i] in '"\'':
            q = src[i]; j = i + 1
            while j < n and src[j] != q:
                j += 2 if src[j] == '\\' else 1
            out.append(src[i:j + 1] if keep_strings else q + 'S' * 0 + q); i = j + 1
        else:
            out.append(src[i]); i += 1
    return ''.join(out)

def split_args(s):
    args, d, cur, i = [], 0, '', 0
    while i < len(s):
        ch = s[i]
        if ch == '"':
            j = i + 1
            while s[j] != '"': j += 2 if s[j] == '\\' else 1
            cur += s[i:j + 1]; i = j + 1; continue
        if ch in '([{': d += 1
        if ch in ')]}': d -= 1
        if ch == ',' and d == 0: args.append(cur.strip()); cur = ''
        else: cur += ch
        i += 1
    args.append(cur.strip()); return args

for f in FILES:
    raw = open(f).read()
    code = strip(raw, False)
    print(f.split('/')[-1], 'balance: {}', code.count('{') - code.count('}'), ' ()', code.count('(') - code.count(')'), ' []', code.count('[') - code.count(']'))
    src = strip(raw, True)
    for m in re.finditer(r'\b(StringFormat|PrintFormat)\s*\(', src):
        i = m.end(); d = 1; j = i
        while d:
            if src[j] == '"':
                k = j + 1
                while src[k] != '"': k += 2 if src[k] == '\\' else 1
                j = k + 1; continue
            if src[j] == '(': d += 1
            elif src[j] == ')': d -= 1
            j += 1
        args = split_args(src[i:j - 1])
        fmt = args[0]
        spec = re.findall(r'%(?!%)[-+ #0]*\d*(?:\.\d+)?[a-zA-Z]', fmt.replace('%%', ''))
        line = raw.count('\n', 0, 0)  # placeholder
        ln = src.count('\n', 0, m.start()) + 1
        ok = len(spec) == len(args) - 1
        print(f'   line~{ln:4d} {m.group(1):12s} specs={spec} nargs={len(args) - 1} {"OK" if ok else "MISMATCH"}')
