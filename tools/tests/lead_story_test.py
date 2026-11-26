"""Every post takes a turn as the lead story. For each, the homepage alone is built with the clock set just after that post,
opened in headless Chrome at a wide and a narrow width, and the page's own test readings are collected."""
import json, os, re, shutil, subprocess, sys, time, html
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
S=os.path.dirname(os.path.abspath(__file__)); SITE=os.path.dirname(os.path.dirname(S))
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
rows=sorted(json.load(open(S+'/profile.json')),key=lambda r:r['date'])
def one(i):
    r=rows[i]; out=f'{S}/t/{i}'; res=dict(i=i,slug=r['slug'],date=r['date'])
    now=(datetime.fromisoformat(r['date'])+timedelta(seconds=30)).isoformat()
    b=subprocess.run(['/opt/homebrew/bin/hugo','--quiet','--renderSegments','home','--noBuildLock','--baseURL',f'http://localhost:4177/t/{i}/','--destination',out],cwd=SITE,env=dict(os.environ,HUGO_PARAMS_MOCKNOW=now,HUGO_PARAMS_LEADTEST='1'),capture_output=True,text=True)
    if b.returncode: res['error']=b.stderr[-300:]; return res
    for tag,w,h in (('wide',1300,900),('narrow',390,850)):
        d=subprocess.run([CH,'--headless=new','--disable-gpu',f'--window-size={w},{h}','--virtual-time-budget=5000','--dump-dom',f'http://localhost:4177/t/{i}/'],capture_output=True,text=True,timeout=90).stdout
        m=re.search(r'<section class="g-top[^"]*"([^>]*)>',d); a=dict(re.findall(r'data-(\w+)="([^"]*)"',m.group(1))) if m else {}
        top=d[d.find('<section class="g-top'):d.find('<section class="g-secs"')]
        lead_title=html.unescape(re.sub(r'<[^>]+>','',re.search(r'<h2>(.*?)</h2>',top,re.S).group(1))).strip() if '<h2>' in top else ''
        res[tag]=dict(state=a.get('lead'),hidden=a.get('hidden'),gap=a.get('gap'),side=a.get('side'),cont=top.count('class="g-cont"'),fig='class="g-fig"' in top,title_ok=(lead_title==r['title'].strip()),two='g-top two' in d)
    shutil.rmtree(out,ignore_errors=True)
    return res
if __name__=='__main__':
    idx=list(range(len(rows))); t=time.time()
    if '--sample' in sys.argv:   # a random sample, for a site with too many posts to try every one
        import random; random.seed(1); idx=sorted(random.sample(idx,min(len(idx),int(sys.argv[sys.argv.index('--sample')+1]))))
    with ThreadPoolExecutor(3) as ex: out=list(ex.map(one,idx))
    json.dump(out,open(S+'/alltest.json','w'))
    print('done',len(out),'posts in',round(time.time()-t),'seconds')
