"""Train a compact conditional piano neural network from scratch, using NumPy.

No song archive is written to disk. MAESTRO is streamed into memory and its
official composition-disjoint train/validation/test split is retained.
"""
import os
os.environ.setdefault('VECLIB_MAXIMUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
import argparse
import collections
import hashlib
import io
import json
import math
import struct
import time
import urllib.request
import unicodedata
import zipfile
from pathlib import Path
import numpy as np

URL = 'https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0-midi.zip'
SHA = '70470ee253295c8d2c71e6d9d4a815189e35c89624b76d22fce5a019d5dde12c'
RHYTHMS = [.25, .5, .75, 1., 1.5, 2., 3., 4.]
DURATIONS = [.2, .35, .5, .75, 1., 1.5, 2., 3.]
HEADS = [61, 8, 8, 8, 12, 3]
FEATURES = 39
TRIADS = [(0, 4, 7), (0, 3, 7), (0, 3, 6)]
KEY_PROFILES = [np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]),
                np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])]

def vlq(b, pos):
    value = 0
    for _ in range(4):
        c = b[pos]; pos += 1
        value = (value << 7) | (c & 127)
        if not c & 128:
            return value, pos
    raise ValueError('Invalid MIDI VLQ')

def midi_notes(blob, programs=None):
    """Read MIDI 0/1 tempo maps and note lifetimes, without external packages."""
    if blob[:4] != b'MThd':
        raise ValueError('Invalid MIDI header')
    length = struct.unpack('>I', blob[4:8])[0]
    fmt, tracks, division = struct.unpack('>HHH', blob[8:14])
    if division & 32768 or fmt > 1:
        raise ValueError('Unsupported MIDI time division or format')
    pos, events = 8+length, []
    for track in range(tracks):
        if blob[pos:pos+4] != b'MTrk':
            raise ValueError('Missing MIDI track')
        size = struct.unpack('>I', blob[pos+4:pos+8])[0]
        data = blob[pos+8:pos+8+size]; pos += size+8
        j, tick, running = 0, 0, None
        while j < len(data):
            delta, j = vlq(data, j); tick += delta
            status = data[j]
            if status & 128:
                j += 1
                if status < 240:
                    running = status
            elif running is not None:
                status = running
            else:
                raise ValueError('Missing running status')
            if status == 255:
                kind = data[j]; j += 1
                n, j = vlq(data, j)
                payload = data[j:j+n]; j += n
                if kind == 81 and n == 3:
                    events.append((tick, -1, 'tempo', int.from_bytes(payload, 'big'), 0, 0))
                continue
            if status in [240, 247]:
                n, j = vlq(data, j); j += n
                continue
            kind, channel = status >> 4, status & 15
            n = 1 if kind in [12, 13] else 2
            a = data[j]; b = data[j+1] if n == 2 else 0; j += n
            if channel==9:continue
            if kind == 12:
                events.append((tick,track,'program',channel,a,0))
            if kind == 9 and b:
                events.append((tick, track, 'on', channel, a, b))
            elif kind == 8 or (kind == 9 and not b):
                events.append((tick, track, 'off', channel, a, b))
    events.sort(key=lambda e: (e[0], e[1]))
    tempo, tick, seconds, active, notes = 500000, 0, 0., {}, []
    program_map={}
    for t, track, kind, channel, pitch, velocity in events:
        seconds += (t-tick)*tempo/(division*1e6); tick = t
        if kind == 'tempo':
            tempo = channel; continue
        if kind=='program':
            program_map[(track,channel)]=pitch;continue
        key = (track, channel, pitch)
        if kind == 'on':
            if programs is not None and program_map.get((track,channel),0) not in programs:continue
            if key in active:
                start, v = active.pop(key)
                notes.append((start, max(.03, seconds-start), pitch, v))
            active[key] = (seconds, velocity)
        elif key in active:
            start, v = active.pop(key)
            notes.append((start, max(.03, seconds-start), pitch, v))
    for (_, _, pitch), (start, v) in active.items():
        notes.append((start, max(.03, seconds-start), pitch, v))
    return sorted(notes)

def key_of(notes):
    hist = np.zeros(12)
    for _, dur, pitch, _ in notes:
        hist[pitch % 12] += min(dur, 3)
    h = hist-hist.mean()
    best = (-1e9, 0, 0)
    for mode, profile in enumerate(KEY_PROFILES):
        p = profile-profile.mean()
        for tonic in range(12):
            score = float(h @ np.roll(p, tonic)/max(1e-6, np.linalg.norm(h)*np.linalg.norm(p)))
            if score > best[0]:
                best = (score, tonic, mode)
    return best[1:]

def frames_from(notes):
    """Approximate upper voice and local harmony from clustered performed onsets."""
    groups = []
    for note in notes:
        if 28 <= note[2] <= 105:
            if not groups or note[0]-groups[-1][0][0] > .035:
                groups.append([note])
            else:
                groups[-1].append(note)
    if len(groups) < 40:
        return [], 0, 0, .6
    tonic, mode = key_of(notes)
    gaps = np.diff([g[0][0] for g in groups])
    useful = gaps[(gaps > .06) & (gaps < 2)]
    if not len(useful):useful=np.array([.6])
    candidates = np.linspace(.36, .9, 70)
    grid = np.array(RHYTHMS)
    # Performed MIDI does not have a reliable notated beat: infer a coarse pulse.
    scores = [np.minimum(np.abs(useful[:, None]/b-grid), 1).min(axis=1).mean()+.035*abs(b-.6)
              for b in candidates]
    beat = float(candidates[int(np.argmin(scores))])
    out = []
    last_root, last_quality = 0, mode
    for i, group in enumerate(groups):
        upper = max(group, key=lambda n:n[2])
        if not 36 <= upper[2]-tonic <= 96:
            continue
        start, dur, pitch, velocity = upper
        recent = [n for g in groups[max(0,i-3):i+1] for n in g if start-n[0] < beat*1.5]
        pcs = collections.Counter((n[2]-tonic)%12 for n in recent)
        bass_pc = (min(group,key=lambda n:n[2])[2]-tonic)%12
        best = (-1e9, last_root, last_quality)
        for root in range(12):
            for quality, shape in enumerate(TRIADS):
                inside = sum(pcs[(root+s)%12] for s in shape)
                score = inside-.4*(sum(pcs.values())-inside)+.6*(root==bass_pc)
                if score > best[0]:
                    best = score, root, quality
        _, last_root, last_quality = best
        next_start = groups[i+1][0][0] if i+1<len(groups) else start+beat
        rhythm = int(np.argmin(np.abs(grid-(next_start-start)/beat)))
        duration = int(np.argmin(np.abs(np.array(DURATIONS)-dur/beat)))
        out.append([pitch-tonic-36, rhythm, duration, min(7,max(0,(velocity-32)//8)), last_root, last_quality])
    return out, tonic, mode, beat

def feature(history, mode, phase):
    values = []
    padded = ([[history[0][0],3,3,4,0,mode]]*max(0,8-len(history))) + history[-8:]
    previous = padded[0][0]
    for f in padded:
        values += [(f[0]-24)/36, max(-2,min(2,(f[0]-previous)/12)), (f[1]-3)/4, (f[3]-3.5)/4]
        previous = f[0]
    root, quality = padded[-1][4:6]
    values += [math.sin(root*math.tau/12), math.cos(root*math.tau/12), quality/2,
               float(mode), math.sin(phase*math.tau/4), math.cos(phase*math.tau/4), len(history)%8/8]
    return values

def fingerprint(frames):
    # Transposition-invariant 20-event fingerprints. Not stored/replayable music.
    h = 2166136261
    for i in range(1,len(frames)):
        for value in [frames[i][0]-frames[i-1][0]+64, frames[i-1][1]]:
            h = ((h ^ value)*16777619) & 0xffffffff
    return h


REPERTOIRE_ARCHIVE=None
def repertoire_bytes(path):
    global REPERTOIRE_ARCHIVE
    if path.exists():return path.read_bytes()
    if REPERTOIRE_ARCHIVE is None:REPERTOIRE_ARCHIVE=zipfile.ZipFile(path.parent/"public-domain-midi.zip")
    return REPERTOIRE_ARCHIVE.read(path.name)

def load_dataset(family=None):
    rows=[]
    if family is None:
        print('Streaming 56 MB MAESTRO archive into memory...',flush=True)
        with urllib.request.urlopen(URL,timeout=120) as response:
            blob = response.read()
        if hashlib.sha256(blob).hexdigest()!=SHA:
            raise ValueError('Training archive checksum mismatch')
        archive = zipfile.ZipFile(io.BytesIO(blob))
        metadata = json.loads(archive.read('maestro-v3.0.0/maestro-v3.0.0.json'))
        rows = [{k:v[str(i)] for k,v in metadata.items()} for i in range(len(metadata['split']))] if isinstance(metadata,dict) else metadata
    data = {s:[[],[]] for s in ['train','validation','test']}
    hashes, stats = set(), collections.Counter()
    for i,row in enumerate(rows if family is None else []):
        notes = midi_notes(archive.read('maestro-v3.0.0/'+row['midi_filename']))
        frames, tonic, mode, beat = frames_from(notes)
        split = row['split']
        stats[split+'_performances'] += 1
        stats[split+'_frames'] += len(frames)
        if split=='train':
            for j in range(20,len(frames),4):
                hashes.add(fingerprint(frames[j-20:j]))
        # Bounded memory: every third onset, preserving its preceding context.
        phase = 0.
        for j in range(1,len(frames)):
            if j%3==0:
                data[split][0].append(feature(frames[max(0,j-8):j],mode,phase))
                data[split][1].append(frames[j])
            phase += RHYTHMS[frames[j-1][1]]
        if i%50==0:
            print(f'Parsed {i}/{len(rows)} performances',flush=True)
    # Add only composers absent from MAESTRO, conservatively preventing
    # alternate editions of MAESTRO validation/test works entering training.
    def surname(name):
        name=unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode()
        result=re.sub('[^a-z]','',name.split('(')[0].strip().split()[-1].lower())
        return {'mendelssohnbartholdy':'mendelssohn','rachmaninov':'rachmaninoff'}.get(result,result)
    import re
    existing={surname(part) for r in rows for part in r['canonical_composer'].split('/')}
    if family:
        provenance_path=Path(__file__).parent/'dist/repertoire-provenance.json'
        baseline_names=json.loads(provenance_path.read_text()).get('maestro_composer_counts',{})
        existing={surname(part) for name in baseline_names for part in name.split('/')} 
    manifest_path=Path(__file__).parent/'repertoire'/'manifest.json'
    provenance=[];excluded=0
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        specialist_splits={}
        if family:
            family_programs={'violin':[40,41],'cello':[42,43],'flute':[73,72],'harp':[46],'strings':[48,49,50,51],'clarinet':[71],'bassoon':[70]}
            eligible=set()
            for r in manifest['records']:
                ns=midi_notes(repertoire_bytes(manifest_path.parent/r['file']),family_programs[family])
                if len(ns)>=40:eligible.add(r['composer'])
            groups=sorted(eligible,key=lambda c:hashlib.sha256(c.encode()).hexdigest())
            if len(groups)<3:raise ValueError('At least three composers are needed for composer-disjoint specialist evaluation')
            held=max(1,len(groups)//5)
            specialist_splits={c:('validation' if i<held else 'test' if i<2*held else 'train') for i,c in enumerate(groups)}
        for record in manifest['records']:
            if family is None and surname(record['composer']) in existing:
                excluded+=1;continue
            families={'violin':[40,41],'cello':[42,43],'flute':[73,72],'harp':[46],'strings':[48,49,50,51],'clarinet':[71],'bassoon':[70]}
            notes=midi_notes(repertoire_bytes(manifest_path.parent/record['file']), families[family] if family else None)
            if family in ['cello','bassoon']:notes=[(t,d,p+12 if p<60 else p,v) for t,d,p,v in notes]
            frames,tonic,mode,beat=frames_from(notes)
            if len(frames)<40:continue
            group=record['composer']+'|'+record['source_page']
            split_value=int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%10
            split=specialist_splits.get(record['composer'],'train') if family else ('validation' if split_value==0 else 'test' if split_value==1 else 'train')
            stats[split+'_performances']+=1;stats[split+'_frames']+=len(frames)
            phase=0.
            for j in range(1,len(frames)):
                if j%3==0:
                    data[split][0].append(feature(frames[max(0,j-8):j],mode,phase));data[split][1].append(frames[j])
                phase+=RHYTHMS[frames[j-1][1]]
            if split=='train':
                for j in range(20,len(frames),4):hashes.add(fingerprint(frames[j-20:j]))
            provenance.append({**record,'split':split,'extracted_frames':len(frames)})
        stats['mutopia_added_files']=len(provenance);stats['mutopia_existing_composer_files_excluded']=excluded
        (Path(__file__).parent/'dist'/('repertoire-provenance.json' if family is None else family+'-provenance.json')).write_text(json.dumps({'records':provenance,
            'selection':('Composer-disjoint specialist splits; initialized from scratch.' if family else 'Composers absent from MAESTRO only, preventing cross-source composer/work overlap in held-out tests.'),
            'maestro_composer_counts':dict(collections.Counter(r['canonical_composer'] for r in rows if r['split']=='train'))},indent=2))
    arrays = {s:(np.asarray(x,dtype=np.float32),np.asarray(y,dtype=np.int16)) for s,(x,y) in data.items()}
    print('Prepared',dict(stats),flush=True)
    return arrays, hashes, dict(stats)

def softmax(z):
    z = z-z.max(axis=1,keepdims=True)
    p = np.exp(z)
    return p/p.sum(axis=1,keepdims=True)

def evaluate(params,x,y,batch=1024):
    losses = np.zeros(len(HEADS)); count = 0
    for start in range(0,len(x),batch):
        xb,yb = x[start:start+batch],y[start:start+batch]
        h1 = np.tanh(xb@params['w1']+params['b1'])
        h2 = np.tanh(h1@params['w2']+params['b2'])
        z = h2@params['w3']+params['b3']
        offset=0
        for head,size in enumerate(HEADS):
            p=softmax(z[:,offset:offset+size])
            losses[head] += -np.log(np.maximum(p[np.arange(len(xb)),yb[:,head]],1e-9)).sum()
            offset+=size
        count+=len(xb)
    return (losses/count).tolist()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--epochs',type=int,default=6)
    ap.add_argument('--out',type=Path,default=Path(__file__).parent/'dist')
    ap.add_argument('--hidden',type=int,default=192)
    ap.add_argument('--family',choices=['violin','cello','flute','harp','strings','clarinet','bassoon'])
    ap.add_argument('--init',type=Path)
    ap.add_argument('--seed',type=int,default=73619)
    a=ap.parse_args()
    rng=np.random.default_rng(a.seed)
    data,hashes,stats=load_dataset(a.family)
    x,y=data['train']; vx,vy=data['validation']; tx,ty=data['test']
    hidden=a.hidden
    params={}
    for layer,(ins,outs) in enumerate([(FEATURES,hidden),(hidden,hidden),(hidden,sum(HEADS))],1):
        params[f'w{layer}']=(rng.normal(size=(ins,outs))*math.sqrt(1/ins)).astype(np.float32)
        params[f'b{layer}']=np.zeros(outs,dtype=np.float32)
    if min(len(x),len(vx),len(tx))<100:raise ValueError('Insufficient independent instrument training/validation/test data')
    if a.init:
        initial=json.loads(a.init.read_text())
        params={k:np.array(w['values'],dtype=np.float32).reshape(w['shape']) for k,w in initial['weights'].items()}
        hidden=params['b1'].size
    m={k:np.zeros_like(v) for k,v in params.items()}; v={k:np.zeros_like(p) for k,p in params.items()}
    baseline=[]
    for head,size in enumerate(HEADS):
        p=(np.bincount(y[:,head],minlength=size)+1)/(len(y)+size)
        baseline.append(float(-np.log(p[vy[:,head]]).mean()))
    before=evaluate(params,vx,vy)
    history=[]; best_loss=float('inf'); best=None; step=0; began=time.monotonic()
    print(f'Training {sum(v.size for v in params.values()):,} neural parameters; {len(x):,} examples',flush=True)
    for epoch in range(a.epochs):
        order=rng.permutation(len(x)); training=[]
        for start in range(0,len(order),512):
            ids=order[start:start+512]; xb,yb=x[ids],y[ids]; n=len(ids)
            h1=np.tanh(xb@params['w1']+params['b1'])
            h2=np.tanh(h1@params['w2']+params['b2'])
            z=h2@params['w3']+params['b3']; dz=np.zeros_like(z); loss=0.; offset=0
            for head,size in enumerate(HEADS):
                p=softmax(z[:,offset:offset+size])
                loss+=float(-np.log(np.maximum(p[np.arange(n),yb[:,head]],1e-9)).mean())
                p[np.arange(n),yb[:,head]]-=1
                dz[:,offset:offset+size]=p/n/len(HEADS); offset+=size
            dh2=(dz@params['w3'].T)*(1-h2*h2)
            dh1=(dh2@params['w2'].T)*(1-h1*h1)
            grads={'w3':h2.T@dz,'b3':dz.sum(0),'w2':h1.T@dh2,'b2':dh2.sum(0),'w1':xb.T@dh1,'b1':dh1.sum(0)}
            step+=1
            lr=.001*(.35+.65*(1-epoch/max(1,a.epochs)))
            for k in params:
                g=np.clip(grads[k],-1,1)
                m[k]=.9*m[k]+.1*g; v[k]=.999*v[k]+.001*g*g
                params[k]-=lr*(m[k]/(1-.9**step))/(np.sqrt(v[k]/(1-.999**step))+1e-8)
            training.append(loss/len(HEADS))
            if step%200==0:
                print(f'Epoch {epoch+1} step {step} loss {np.mean(training[-200:]):.3f} elapsed {time.monotonic()-began:.0f}s',flush=True)
        validation=evaluate(params,vx,vy)
        record={'epoch':epoch+1,'train_loss':float(np.mean(training)),'validation_heads':validation}
        history.append(record)
        print(json.dumps(record),flush=True)
        if sum(validation)<best_loss:
            best_loss=sum(validation); best={k:p.copy() for k,p in params.items()}
    test=evaluate(best,tx,ty)
    baseline_test=[]
    for head,size in enumerate(HEADS):
        p=(np.bincount(y[:,head],minlength=size)+1)/(len(y)+size)
        baseline_test.append(float(-np.log(p[ty[:,head]]).mean()))
    a.out.mkdir(parents=True,exist_ok=True)
    report={'architecture':'conditional autoregressive MLP, two tanh hidden layers',
      'dataset':('Public-domain Mutopia GM-labelled '+a.family+' parts' if a.family else 'MAESTRO v3.0.0 + public-domain Mutopia editions'),'dataset_sha256':SHA,'source':('https://www.mutopiaproject.org/' if a.family else URL),'license':'CC BY-NC-SA 4.0; Mutopia supplements Public Domain',
      'instrument_family':a.family,'initialized_from':str(a.init) if a.init else None,'seed':a.seed,'hidden':hidden,'features':FEATURES,'heads':['pitch','onset_gap','duration','velocity','harmony_root','harmony_quality'],
      'head_sizes':HEADS,'parameters':sum(p.size for p in best.values()),'statistics':stats,
      'training_examples':len(x),'validation_examples':len(vx),'test_examples':len(tx),
      'validation_initial':before,'validation_unconditional_baseline':baseline,
      'test_loss':test,'test_unconditional_baseline':baseline_test,'history':history,
      'training_seconds':round(time.monotonic()-began,1),'listening_review':'not professionally evaluated',
      'limitations':['Eight-event context; not a long-context Transformer.',
        'Upper-voice and pulse extraction are approximations.',
        'Generation adds musical form, voice-leading and cadence constraints.',
        'Novelty fingerprints are a partial exact-match check, not a proof of originality.']}
    weights={k:{'shape':list(p.shape),'values':[round(float(z),7) for z in p.ravel()]} for k,p in best.items()}
    (a.out/'model.json').write_text(json.dumps({'weights':weights,'report':report},separators=(',',':')))
    (a.out/'training-report.json').write_text(json.dumps(report,indent=2))
    with (a.out/'novelty.bin').open('wb') as f:
        f.write(struct.pack('<'+'I'*len(hashes),*sorted(hashes)))
    print('Saved trained weights and report.',flush=True)

if __name__=='__main__':
    main()
