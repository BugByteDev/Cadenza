"""Download licensed MIDI from Mutopia public-domain editions of major composers."""
import argparse
import concurrent.futures
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import re
import urllib.request
import urllib.parse
import zipfile
from pathlib import Path

BASE='https://www.mutopiaproject.org/'
COMPOSERS=['BachJS','Beethoven','Mozart','Chopin','Schubert','Liszt','Brahms','Schumann','Debussy','Ravel','Satie','Tchaikovsky','Dvor','Grieg','Mendelssohn','Haydn','Handel','Vivaldi','Saint','Rachman','Rimsky','Mussorgsky','Bizet','Faure','Sibelius','Holst','Verdi','Wagner','Purcell','Scarlatti','Rossini','Berlioz','Borodin','Couperin']
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.url=None;self.label=''
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.url=dict(attrs).get('href');self.label=''
    def handle_data(self,data):
        if self.url:self.label+=data
    def handle_endtag(self,tag):
        if tag=='a' and self.url:self.links.append((self.url,self.label.strip()));self.url=None
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'CadenzaRepertoireResearch/1.0'})
    with urllib.request.urlopen(req,timeout=35) as r:return r.read()
def candidates(composer,url):
    page=get(url).decode();pieces=[]
    navigation=Links();navigation.feed(page)
    next_page=next((urllib.parse.urljoin(url,u) for u,label in navigation.links if label=='Next 10'),None)
    for block in re.split(r'<table[^>]*class="[^"]*result-table[^"]*"[^>]*>',page)[1:]:
        block=block.split('</table>')[0]
        if 'Public Domain' not in block:continue
        links=Links();links.feed(block)
        midi=[urllib.parse.urljoin(url,u) for u,label in links.links if re.search(r'\.(?:mid|midi)$|-mids\.zip$',u)]
        if not midi:continue
        title=html.unescape(re.sub('<[^>]+>','',re.search(r'<td[^>]*>(.*?)</td>',block,re.S).group(1))).strip()
        info=next((urllib.parse.urljoin(url,u) for u,l in links.links if 'piece-info' in u),url)
        pieces.append({'composer':composer,'title':title,'license':'Public Domain','source_page':info,'midi_urls':midi})
    words=['symphony','sonata','concerto','moonlight','elise','clair','lune','spring','seasons','swan','canon','humoresque','gymnop','arabesque','hungarian','pavane','nocturne','waltz','toccata','goldberg']
    pieces.sort(key=lambda p:sum(w in p['title'].lower() for w in words),reverse=True)
    return pieces+(candidates(composer,next_page) if next_page else [])

def main():
    out=Path(__file__).parent/'repertoire';out.mkdir(exist_ok=True)
    links=Links();links.feed(get(BASE+'browse.html').decode())
    selected=[]
    for url,label in links.links:
        if 'Composer=' not in url:continue
        code=urllib.parse.parse_qs(urllib.parse.urlparse(html.unescape(url)).query).get('Composer',[''])[0]
        if code:selected.append((label,urllib.parse.urljoin(BASE,html.unescape(url))))
    pieces=[];errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(candidates,c,u):c for c,u in selected}
        for f in concurrent.futures.as_completed(futures):
            c=futures[f]
            try:found=f.result();pieces+=found;print(c,len(found),'public-domain editions',flush=True)
            except Exception as e:errors.append({'composer':c,'error':str(e)})
    old=json.loads((out/'manifest.json').read_text()) if (out/'manifest.json').exists() else {'records':[]}
    cache={}
    for r in old['records']:cache.setdefault(r['download_url'],[]).append(r)
    def fetch_piece(item):
        piece,url=item
        if url in cache:return cache[url]
        blob=get(url)
        if url.endswith('.zip'):
            z=zipfile.ZipFile(io.BytesIO(blob));files=[(n,z.read(n)) for n in z.namelist() if n.lower().endswith(('.mid','.midi'))]
        else:files=[(url.rsplit('/',1)[-1],blob)]
        result=[]
        for name,data in files:
            if data[:4]!=b'MThd':continue
            sha=hashlib.sha256(data).hexdigest();filename=sha+'.mid';(out/filename).write_bytes(data)
            result.append({**piece,'download_url':url,'archive_member':name,'sha256':sha,'file':filename})
        return result
    records=[];seen=set()
    jobs=[(piece,url) for piece in pieces for url in piece['midi_urls']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(fetch_piece,j):j[1] for j in jobs}
        for i,f in enumerate(concurrent.futures.as_completed(futures)):
            try:
                for r in f.result():
                    if r['sha256'] not in seen:seen.add(r['sha256']);records.append(r)
            except Exception as e:errors.append({'url':futures[f],'error':str(e)})
            if i%100==0:print('Downloaded sources',i,'/',len(jobs),flush=True)
    manifest={'source':'Mutopia Project','license_filter':'Public Domain only','selection':'All available public-domain MIDI editions returned by composer catalogue pages; not a claim of all classical music.', 'records':records,'errors':errors}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2));print('Downloaded',len(records),'MIDI files',flush=True)
if __name__=='__main__':main()
