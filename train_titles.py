"""Separate neural word model for newly sampled, readable composition titles."""
import os
os.environ.setdefault('VECLIB_MAXIMUM_THREADS','2')
import collections
import hashlib
import json
import math
import re
import urllib.request
from pathlib import Path
import numpy as np

SOURCE='https://www.gutenberg.org/ebooks/12242.txt.utf-8'
def hash_title(words):
    h=2166136261
    for byte in ' '.join(words).encode():h=((h^byte)*16777619)&0xffffffff
    return h
def main():
    blob=urllib.request.urlopen(SOURCE,timeout=60).read();text=blob.decode().replace('\r','')
    text=text[text.index('I. LIFE.'):].split('*** END OF THE PROJECT GUTENBERG')[0]
    groups=re.split(r'(?m)^\s*[IVXLC]+\.\s*$',text)[1:]
    examples=[];counts=collections.Counter();all_lines=[]
    for group_id,group in enumerate(groups):
        for line in group.splitlines():
            line=line.strip().lower().replace("ne'er",'never').replace("o'er",'over').replace("'t is",'it is')
            if not line or any(c.isdigit() for c in line) or '[' in line or ']' in line:continue
            words=re.findall(r"[a-z]+(?:'[a-z]+)?",line)
            if not 2<=len(words)<=8:continue
            if any(len(w)>16 for w in words):continue
            examples.append((group_id,words));counts.update(words);all_lines.append(words)
    vocab=['<pad>','<bos>','<eos>']+[w for w,n in counts.most_common() if n>=3]
    index={w:i for i,w in enumerate(vocab)}
    x={'train':[],'validation':[]};y={'train':[],'validation':[]}
    for group,words in examples:
        if any(w not in index for w in words):continue
        split='validation' if group%10==0 else 'train';history=[0,0,0,1]
        for target in [index[w] for w in words]+[2]:
            x[split].append(history[-4:]);y[split].append(target);history.append(target)
    x={s:np.array(v,dtype=np.int32) for s,v in x.items()};y={s:np.array(v,dtype=np.int32) for s,v in y.items()}
    rng=np.random.default_rng(41927);embedding=32;hidden=96
    params={'e':rng.normal(0,.12,(len(vocab),embedding)).astype(np.float32),
      'w1':rng.normal(0,.08,(embedding*4,hidden)).astype(np.float32),'b1':np.zeros(hidden,dtype=np.float32),
      'w2':rng.normal(0,.08,(hidden,len(vocab))).astype(np.float32),'b2':np.zeros(len(vocab),dtype=np.float32)}
    m={k:np.zeros_like(v) for k,v in params.items()};v={k:np.zeros_like(p) for k,p in params.items()};step=0
    def predict(xb):
        z=params['e'][xb].reshape(len(xb),-1);h=np.tanh(z@params['w1']+params['b1']);logits=h@params['w2']+params['b2'];logits-=logits.max(1,keepdims=True);p=np.exp(logits);p/=p.sum(1,keepdims=True);return z,h,p
    def evaluate():
        losses=[]
        for i in range(0,len(x['validation']),256):
            xb=x['validation'][i:i+256];yb=y['validation'][i:i+256];p=predict(xb)[2];losses.extend(-np.log(np.maximum(1e-9,p[np.arange(len(xb)),yb])))
        return float(np.mean(losses))
    initial=evaluate();best=float('inf');best_params=None;history=[]
    for epoch in range(25):
        order=rng.permutation(len(x['train']));losses=[]
        for start in range(0,len(order),256):
            ids=order[start:start+256];xb=x['train'][ids];yb=y['train'][ids];z,h,p=predict(xb);n=len(xb)
            losses.append(float(-np.log(np.maximum(1e-9,p[np.arange(n),yb])).mean()))
            p[np.arange(n),yb]-=1;p/=n;dh=(p@params['w2'].T)*(1-h*h)
            grads={'w2':h.T@p,'b2':p.sum(0),'w1':z.T@dh,'b1':dh.sum(0),'e':np.zeros_like(params['e'])}
            de=(dh@params['w1'].T).reshape(n,4,embedding)
            np.add.at(grads['e'],xb,de)
            step+=1
            for k in params:
                g=np.clip(grads[k],-1,1);m[k]=.9*m[k]+.1*g;v[k]=.999*v[k]+.001*g*g
                params[k]-=.002*(m[k]/(1-.9**step))/(np.sqrt(v[k]/(1-.999**step))+1e-8)
        val=evaluate();history.append({'epoch':epoch+1,'train_loss':float(np.mean(losses)),'validation_loss':val})
        if val<best:best=val;best_params={k:p.copy() for k,p in params.items()}
        if epoch%5==0:print(history[-1],flush=True)
    freq=np.bincount(y['train'],minlength=len(vocab))+1;freq=freq/freq.sum();baseline=float(-np.log(freq[y['validation']]).mean())
    report={'architecture':'four-word context embedding neural language model','parameters':sum(p.size for p in best_params.values()),
      'source':SOURCE,'source_title':'Poems by Emily Dickinson, Three Series, Complete','author':'Emily Dickinson (1830–1886)',
      'source_sha256':hashlib.sha256(blob).hexdigest(),'training_type':'public-domain verse lines and headings, not a stored title catalogue',
      'training_examples':len(x['train']),'validation_examples':len(x['validation']),'poem_groups':len(groups),
      'vocabulary':len(vocab),'initial_validation_loss':initial,'best_validation_loss':best,'frequency_baseline_loss':baseline,
      'history':history,'seed':41927,'limitations':['Small English poetic language model; names use readability and exact-copy filters.','Not a large language model; human judgments of title quality vary.']}
    weights={k:{'shape':list(p.shape),'values':[round(float(z),7) for z in p.ravel()]} for k,p in best_params.items()}
    out=Path(__file__).parent/'dist'
    (out/'title-model.json').write_text(json.dumps({'vocabulary':vocab,'weights':weights,'training_hashes':sorted({hash_title(w) for w in all_lines}),'report':report},separators=(',',':')))
    (out/'title-training-report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='history'}),flush=True)
if __name__=='__main__':main()
