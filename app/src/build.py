import sys,glob,subprocess
import os
d=os.path.dirname(os.path.abspath(__file__))+'/'
# nothing may be asked before it is taught (v2 lessons)
if subprocess.run(['node',d+'i18n/tools/check_taught.js']).returncode: sys.exit('build stopped: fix the lessons above')
content=''.join(open(d+f).read()+'\n' for f in ['c0.js','c1.js','c2.js','ck.js','c3.js','c4.js','c5.js','c6.js','c7.js','v2_h12.js']+sorted(x[len(d):] for x in glob.glob(d+'simple/*.js'))+['en_ui.js','en_c.js'])
s=open(d+'shell.html').read().replace('/*CONTENT*/',content).replace('/*APP*/',open(d+'app.js').read())
open(d+'kodalkhan-publish-source.html','w').write(s)
print(len(s))
