import glob, re, os, yaml, json, html, subprocess
rows=[]
for f in sorted(glob.glob('content/posts/*')):
    t=open(f,encoding='utf-8').read(); _,fm,body=t.split('---\n',2); fm=yaml.safe_load(fm)
    ps=[re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',p))).strip() for p in re.findall(r'(?s)<p[^>]*>.*?</p>',body)]
    ps=[p for p in ps if p]
    plain=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',re.sub(r'\{\{<[^>]*>\}\}','',body)))).strip()
    img=fm.get('image'); dims=None
    if img:
        p='assets/'+img
        if os.path.exists(p) and not p.endswith('.svg'):
            o=subprocess.run(['sips','-g','pixelWidth','-g','pixelHeight',p],capture_output=True,text=True).stdout
            m=re.findall(r'pixel\w+: (\d+)',o); dims=tuple(map(int,m)) if len(m)==2 else None
    rows.append(dict(slug=fm.get('slug') or os.path.basename(f)[:-5],date=str(fm['date']),title=fm['title'],tlen=len(fm['title']),img=img,dims=dims,size=os.path.getsize('assets/'+img) if img and os.path.exists('assets/'+img) else 0,
        np=len(ps),ptext=sum(len(p) for p in ps),plain=len(plain),p1=len(ps[0]) if ps else 0,li=len(re.findall(r'<li',body)),bq=len(re.findall(r'<blockquote',body)),iframe=len(re.findall(r'<iframe',body)),bm=len(re.findall(r'kg-bookmark-container',body)),
        inimg=len(re.findall(r'<img',body)),orig=bool(fm.get('original')),guest=bool(fm.get('contributors')),sec=(fm.get('sections') or [''])[0],src=bool(fm.get('sources'))))
json.dump(rows,open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'profile.json'),'w'))
n=len(rows); noimg=[r for r in rows if not r['img'] or r['img'].endswith('.svg')]
print('posts',n,'no usable picture',len(noimg))
print('no picture and no paragraph text',[r['slug'][:50] for r in noimg if r['ptext']<40])
print('no picture, text under 200 chars',len([r for r in noimg if r['ptext']<200]),[ (r['slug'][:40],r['ptext'],r['plain']) for r in noimg if r['ptext']<200][:8])
print('no picture, text outside paragraphs (plain much longer than p text)',[(r['slug'][:40],r['ptext'],r['plain'],r['li']) for r in noimg if r['plain']-r['ptext']>300][:8])
print('no picture with embed',[(r['slug'][:40],r['iframe'],r['bm'],r['ptext']) for r in noimg if r['iframe'] or r['bm']][:8])
print('title len: max',sorted([(r['tlen'],r['slug'][:40]) for r in rows])[-4:],' min',sorted([(r['tlen'],r['title']) for r in rows])[:4])
withimg=[r for r in rows if r['dims']]
print('pictures: small files',sorted([(r['size'],r['dims'],r['slug'][:36]) for r in withimg])[:6])
print('tall pictures',[(r['dims'],r['slug'][:36]) for r in withimg if r['dims'][1]>r['dims'][0]*1.2][:6])
print('wide pictures',[(r['dims'],r['slug'][:36]) for r in withimg if r['dims'][0]>r['dims'][1]*2.5][:6])
print('tiny pictures',[(r['dims'],r['slug'][:36]) for r in withimg if r['dims'][0]<400][:8])
print('svg',[r['slug'][:40] for r in rows if r['img'] and r['img'].endswith('.svg')][:4])
print('guest',[(r['slug'][:40],bool(r['img'])) for r in rows if r['guest']],' original no pic',[(r['slug'][:40],r['ptext']) for r in noimg if r['orig']][:4])
print('first paragraph very short (<40)',[(r['slug'][:40],r['p1'],r['np']) for r in noimg if 0<r['p1']<40][:8])
