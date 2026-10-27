"""Translate the indicator to C++ against mql5_shim.h, keeping line numbers
(prototypes go on the blank line 83 so every later line keeps its number)."""
import re, sys
src_path, out_path, PROTO_LINE = sys.argv[1], sys.argv[2], int(sys.argv[3])
lines = open(src_path).read().split('\n')
code = '\n'.join(lines)
# user function headers -> prototypes
protos = []
for m in re.finditer(r'^((?:[A-Za-z_]\w*\s+)+[A-Za-z_]\w*\s*\([^;{]*\))\s*\n\{', code, re.M):
    h = re.sub(r'\s+', ' ', m.group(1))
    if not h.split('(')[0].split()[-1].startswith('On'):
        protos.append(re.sub(r'const (\w+) &(\w+)\[\]', r'const DynArr<\1> &\2', h) + ';')
out = []
for i, l in enumerate(lines, 1):
    if l.startswith('#property'):
        l = '//' + l
    elif re.match(r'^input group ', l):
        l = '//' + l
    l = re.sub(r'^input\s', 'const ', l)
    l = re.sub(r"C'(\d+),(\d+),(\d+)'", r'RGB_(\1,\2,\3)', l)
    l = re.sub(r'const (\w+) &(\w+)\[\]', r'const DynArr<\1> &\2', l)
    # dynamic array declarations: T a[], b[];
    m = re.match(r'^(\s*)(\w+)\s+(\w+\[\](?:\s*,\s*\w+\[\])*)\s*;(.*)$', l)
    if m:
        names = re.findall(r'(\w+)\[\]', m.group(3))
        l = f'{m.group(1)}DynArr<{m.group(2)}> {", ".join(names)};{m.group(4)}'
    if i == PROTO_LINE:
        assert l.strip() == '', l
        l = ' '.join(protos)
    out.append(l)
out[0] = '#include "mql5_shim.h"  ' + out[0]; open(out_path, 'w').write('\n'.join(out))
print('\n'.join(protos))
