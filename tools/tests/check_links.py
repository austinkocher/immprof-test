"""Checks a built site folder: every internal link, picture, script and stylesheet address must be a file in the folder.
Also reports pages with no title, no h1, duplicate ids, and pictures with no alt attribute. Usage: python3 linkcheck.py PUBLIC_DIR"""
import os, re, sys, collections, html
from urllib.parse import urlparse, unquote
root=sys.argv[1].rstrip('/')
pages=[os.path.join(d,f) for d,_,fs in os.walk(root) for f in fs if f.endswith('.html') and '/pagefind/' not in d and '/admin' not in d]
bad=collections.defaultdict(set); noalt=0; notitle=[]; noh1=[]; dupid=collections.Counter(); n=0
def exists(path):
    p=unquote(path.split('#')[0].split('?')[0])
    if not p.startswith('/'): return True
    t=root+p
    return os.path.isfile(t) or os.path.isfile(os.path.join(t,'index.html')) or os.path.isfile(t.rstrip('/')+'/index.html')
for pg in pages:
    h=open(pg,encoding='utf-8',errors='ignore').read(); rel=pg[len(root):]
    if 'http-equiv="refresh"' in h[:600]: continue
    n+=1
    if not re.search(r'<title>[^<]+</title>',h): notitle.append(rel)
    if h.count('<h1')!=1 and rel not in('/index.html',) and not re.match(r'^/page/\d+/index.html$',rel): noh1.append((rel,h.count('<h1')))
    ids=re.findall(r'\sid="([^"]+)"',h)
    for k,c in collections.Counter(ids).items():
        if c>1: dupid[k]+=1
    for m in re.finditer(r'<img\b[^>]*>',h):
        if ' alt=' not in m.group(0): noalt+=1
    for a in re.findall(r'(?:href|src)="([^"]+)"',h):
        a=html.unescape(a); u=urlparse(a)
        if u.scheme in('mailto','data','javascript','tel'): continue
        if u.netloc and 'localhost' not in u.netloc: continue
        path=u.path if (u.netloc or a.startswith('/')) else None
        if path is None: continue
        if not exists(path): bad[path].add(rel)
print(root.split('/')[-2],'pages',n)
print('  broken internal addresses',len(bad))
for k,v in sorted(bad.items(),key=lambda x:-len(x[1]))[:12]: print('   ',k[:90],'on',len(v),'pages, e.g.',sorted(v)[0][:60])
print('  pages with no title',len(notitle),notitle[:3]); print('  pages without exactly one h1',len(noh1),noh1[:5])
print('  ids repeated on a page',dict(dupid.most_common(6))); print('  pictures with no alt attribute',noalt)
