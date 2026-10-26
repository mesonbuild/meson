import sys

with open(sys.argv[1], encoding='utf-8') as f, open(sys.argv[2], encoding='utf-8') as g:
    if f.read() != g.read():
        sys.exit('contents are not equal')
