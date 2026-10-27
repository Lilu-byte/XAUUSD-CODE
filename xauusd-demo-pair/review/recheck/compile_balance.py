import sys, re
for p in sys.argv[1:]:
    src = open(p, encoding='utf-8').read()
    # strip comments and strings
    s = re.sub(r'//[^\n]*', '', src)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'"(\\.|[^"\\])*"', '""', s)
    s = re.sub(r"C'[^']*'", "0", s)
    st = []
    pairs = {')':'(', ']':'[', '}':'{'}
    line = 1
    ok = True
    for ch in s:
        if ch == '\n': line += 1
        if ch in '([{': st.append((ch, line))
        elif ch in ')]}':
            if not st or st[-1][0] != pairs[ch]:
                print(p, 'mismatch', ch, 'line', line); ok = False; break
            st.pop()
    if st and ok: print(p, 'unclosed', st[-3:])
    elif ok: print(p, 'balanced')
    # statements ending: lines in code w/o ; that look like statements
