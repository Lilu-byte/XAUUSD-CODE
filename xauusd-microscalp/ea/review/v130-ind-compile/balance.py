import sys, re
src = open(sys.argv[1]).read()
# strip comments and strings, keep line structure
out=[];i=0;n=len(src);line=1
stack=[]
issues=[]
while i<n:
    ch=src[i]
    if src.startswith('//',i):
        j=src.find('\n',i); i = n if j<0 else j; continue
    if src.startswith('/*',i):
        j=src.find('*/',i); line+=src[i:j].count('\n'); i=j+2; continue
    if ch=='"':
        j=i+1
        while src[j]!='"':
            if src[j]=='\\': j+=1
            if src[j]=='\n': issues.append(('newline in string',line))
            j+=1
        i=j+1; continue
    if ch=="'":
        j=src.find("'",i+1); i=j+1; continue
    if ch=='\n': line+=1
    if ch in '([{': stack.append((ch,line))
    elif ch in ')]}':
        o={')':'(',']':'[','}':'{'}[ch]
        if not stack or stack[-1][0]!=o: issues.append(('mismatch '+ch,line))
        else: stack.pop()
    i+=1
print('unclosed:',stack[:5]); print('issues:',issues[:10])
# statements: lines ending without ; { } , ( ) that are code
