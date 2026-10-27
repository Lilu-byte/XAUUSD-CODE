import sys
d=open('data.json').read().replace('</','<\\/')
s=open('shell.html').read().replace('__DATA__',d).replace('__PATTERNS__',open('patterns.js').read()).replace('__APP__',open('app.js').read())
open('gold-pattern-trainer-publish-source.html','w').write(s)
open('gold-pattern-trainer.html','w').write('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><style>body{margin:0}[hidden]{display:none!important}</style></head><body>\n'+s+'\n</body></html>')
