// Conditional neural inference and newly sampled piano composition.
// There are no stored pieces, note phrases, or chord progressions in this file.
const RHYTHMS=[.25,.5,.75,1,1.5,2,3,4], DURATIONS=[.2,.35,.5,.75,1,1.5,2,3];
const HEADS=[61,8,8,8,12,3], TRIADS=[[0,4,7],[0,3,7],[0,3,6]];
const KEYS=['C','C-sharp','D','E-flat','E','F','F-sharp','G','A-flat','A','B-flat','B'];
const TAU=Math.PI*2;
export function random(seed){let a=seed>>>0;return()=>{a+=0x6D2B79F5;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};}
function pick(weights,rng){let total=weights.reduce((a,b)=>a+b,0);if(!(total>0))throw Error('No valid sampling candidates');let v=rng()*total;for(let i=0;i<weights.length;i++){v-=weights[i];if(v<=0)return i;}return weights.length-1;}
function choice(xs,rng){return xs[Math.floor(rng()*xs.length)];}
function feature(history,mode,phase){let padded=history.slice(-8);while(padded.length<8)padded.unshift([history[0][0],3,3,4,0,mode]);let out=[],previous=padded[0][0];for(const f of padded){out.push((f[0]-24)/36,Math.max(-2,Math.min(2,(f[0]-previous)/12)),(f[1]-3)/4,(f[3]-3.5)/4);previous=f[0];}let f=padded.at(-1);out.push(Math.sin(f[4]*TAU/12),Math.cos(f[4]*TAU/12),f[5]/2,mode,Math.sin(phase*TAU/4),Math.cos(phase*TAU/4),0);return out;}
export class NeuralPiano {
  constructor(model){this.report=model.report;this.weights={};for(const [k,v]of Object.entries(model.weights))this.weights[k]={shape:v.shape,values:Float32Array.from(v.values)};}
  layer(x,n,activate){let w=this.weights['w'+n],b=this.weights['b'+n].values,y=Float64Array.from(b);for(let i=0;i<x.length;i++){let xi=x[i],offset=i*y.length;for(let j=0;j<y.length;j++)y[j]+=xi*w.values[offset+j];}if(activate)for(let j=0;j<y.length;j++)y[j]=Math.tanh(y[j]);return y;}
  predict(history,mode,phase,temperature=1){let z=this.layer(this.layer(this.layer(feature(history,mode,phase),1,true),2,true),3,false),offset=0,heads=[];for(const size of HEADS){let logits=Array.from(z.slice(offset,offset+size)),max=Math.max(...logits);heads.push(logits.map(v=>Math.exp((v-max)/temperature)));offset+=size;}return heads;}
}
function fingerprint(frames){let h=2166136261;for(let i=1;i<frames.length;i++)for(const v of[frames[i][0]-frames[i-1][0]+64,frames[i-1][1]])h=Math.imul(h^v,16777619)>>>0;return h;}
function contains(sorted,value){let lo=0,hi=sorted.length;while(lo<hi){let mid=(lo+hi)>>>1;if(sorted[mid]<value)lo=mid+1;else hi=mid;}return sorted[lo]===value;}
function novelty(frames,hashes){if(!hashes?.length)throw Error('Novelty reference unavailable');for(let i=20;i<=frames.length;i++)if(contains(hashes,fingerprint(frames.slice(i-20,i))))return false;return true;}
function nearestTone(pitch,pcs,min,max){let options=[];for(let p=min;p<=max;p++)if(pcs.includes(p%12))options.push(p);return options.sort((a,b)=>Math.abs(a-pitch)-Math.abs(b-pitch))[0];}

export function compose(net,hashes,seed,namer,options={}){
  const rng=random(seed),tonic=Math.floor(rng()*12),mode=rng()<.55?0:1;
  const bpm=72+Math.floor(rng()*49),bars=choice(options.developed?[48,56,64]:[32,40,48],rng),end=bars*4;
  const scale=(mode?[0,2,3,5,7,8,10]:[0,2,4,5,7,9,11]).map(n=>(n+tonic)%12);
  const temperature=.8+rng()*.3,notes=[],chords=[],frames=[],frameBeats=[];
  // A generated opening tone, not a corpus prompt.
  let history=[[36,3,3,4,0,mode]],beat=0,lastPitch=tonic+72,lastRoot=0,lastQuality=mode;
  let firstPhrase=[],rhythmicMemory=[],lastBar=-1;
  while(beat<end-4){
    const bar=Math.floor(beat/4),section=Math.min(3,Math.floor(bar/(bars/4)));
    const cadence=bar%8>=6,isStrong=beat%1<.12;
    const heads=net.predict(history,mode,beat,temperature);
    if(bar!==lastBar){
      let rootWeights=heads[4].map((w,r)=>w*(scale.includes((r+tonic)%12)?1:.08));
      if(cadence)rootWeights=rootWeights.map((w,r)=>w*(r===7?3:r===0?2:.5));
      lastRoot=pick(rootWeights,rng);
      const qualityWeights=heads[5].map((w,q)=>w*(TRIADS[q].every(n=>scale.includes((lastRoot+n+tonic)%12))?1:.06));
      lastQuality=pick(qualityWeights,rng);
      // A structural final dominant, with notes still sampled by the network.
      if(bar===bars-2){lastRoot=7;lastQuality=0;}
      chords.push({beat:bar*4,root:(lastRoot+tonic)%12,quality:lastQuality});lastBar=bar;
    }
    const pcs=TRIADS[lastQuality].map(n=>(lastRoot+n+tonic)%12);
    let pitchWeights=heads[0].map((w,index)=>{
      const pitch=index+tonic+36,distance=Math.abs(pitch-lastPitch);
      if(pitch<60||pitch>91)return 0;
      let factor=scale.includes(pitch%12)?1:.09;
      if(isStrong)factor*=pcs.includes(pitch%12)?1.7:.35;
      factor*=Math.exp(-Math.max(0,distance-4)*.33);
      if(pitch===lastPitch)factor*=.52;
      // Revisit a motif composed earlier in this same generation with variation.
      if((section===1||section===3)&&firstPhrase.length&&isStrong){
        let target=firstPhrase[Math.floor(beat)%firstPhrase.length]+(section===1?0:choice([-2,0,2],rng));
        factor*=Math.exp(-Math.abs(pitch-target)*.15);
      }
      return w*factor;
    });
    let token=pick(pitchWeights,rng),pitch=token+tonic+36;
    let gapWeights=heads[1].map((w,i)=>w*(RHYTHMS[i]<=2?1:.12));
    if(section===2)gapWeights=gapWeights.map((w,i)=>w*(RHYTHMS[i]<1?1.2:.8));
    if(rhythmicMemory.length&&section!==2)gapWeights=gapWeights.map((w,i)=>w*(i===rhythmicMemory[frames.length%rhythmicMemory.length]?1.6:1));
    let rhythm=pick(gapWeights,rng),gap=Math.min(RHYTHMS[rhythm],end-4-beat);
    let dur=pick(heads[2].map((w,i)=>w*(DURATIONS[i]<=gap*1.5?1:.05)),rng);
    let velocity=pick(heads[3],rng);
    let frame=[token,rhythm,dur,velocity,lastRoot,lastQuality];frames.push(frame);frameBeats.push(beat);history.push(frame);
    if(section===0&&bar<4){firstPhrase.push(pitch);rhythmicMemory.push(rhythm);}
    notes.push({beat:beat+(isStrong?0:rng()*.015),duration:Math.min(DURATIONS[dur]*.94,end-beat),pitch,
      velocity:Math.max(34,Math.min(112,34+velocity*8+(isStrong?5:0)+Math.floor(rng()*7))),voice:0});
    lastPitch=pitch;beat+=gap;
  }
  // Close with a tonic cadence; a harmonic rule rather than a stored passage.
  chords.push({beat:end-4,root:tonic,quality:mode});
  const finalPitch=nearestTone(lastPitch,[tonic],60,84);
  notes.push({beat:end-4,duration:3.7,pitch:finalPitch,velocity:58,voice:0});
  let previousBass=tonic+36;
  for(let bar=0;bar<bars;bar++){
    let chord=chords.filter(c=>c.beat<=bar*4).at(-1)||{root:tonic,quality:mode};
    const pcs=TRIADS[chord.quality].map(n=>(chord.root+n)%12);
    let t=bar*4;
    while(t<(bar+1)*4){
      let at=frameBeats.findIndex(b=>b>t);if(at<0)at=frames.length;
      let localHistory=frames.slice(Math.max(0,at-8),at);
      if(!localHistory.length)localHistory=[[36,3,3,4,0,mode]];
      let probe=(options.bassNet||net).predict(localHistory,mode,t,temperature);
      let candidates=[],weights=[];
      for(let p=36;p<=59;p++){
        if(!pcs.includes(p%12))continue;
        candidates.push(p);
        let pcProbability=0;for(let i=0;i<61;i++)if((i+tonic+36)%12===p%12)pcProbability+=probe[0][i];
        weights.push((pcProbability+.001)*Math.exp(-Math.abs(p-previousBass)*.1)*(t%4===0&&p%12===chord.root?3:1));
      }
      const pitch=candidates[pick(weights,rng)];previousBass=pitch;
      let rhythm=pick(probe[1].map((w,i)=>w*(RHYTHMS[i]>=.5&&RHYTHMS[i]<=2?1:.025)),rng);
      let gap=Math.min(RHYTHMS[rhythm],(bar+1)*4-t);
      if(bar===bars-1)gap=4;
      const duration=Math.max(.15,gap*.91);
      notes.push({beat:t,duration,pitch,velocity:43+Math.floor(rng()*18),voice:1});
      if(rng()<.32&&t%1===0){let second=nearestTone(pitch+7,pcs,Math.max(36,pitch+3),59);if(second!==undefined)notes.push({beat:t+.018,duration:Math.max(.15,duration-.018),pitch:second,velocity:37+Math.floor(rng()*13),voice:1});}
      t+=gap;
    }
  }
  // Reattacking a key releases its preceding note, avoiding ambiguous MIDI lifetimes.
  notes.sort((a,b)=>a.beat-b.beat);
  const sounding=new Map();
  for(const note of notes){const key=note.voice+':'+note.pitch,prior=sounding.get(key);
    if(prior&&prior.beat+prior.duration>note.beat)prior.duration=Math.max(.001,note.beat-prior.beat-.001);
    sounding.set(key,note);
  }
  if(!novelty(frames,hashes))throw Error('Exact training-fragment match; resampling required');
  if(!namer&&!options.deferTitle)throw Error('The trained title model is required');
  const title=options.deferTitle?'':namer.generate(random(seed^0x517cc1b7));
  return {title,seed,tonic,mode,bpm,bars,notes,seconds:end*60/bpm,frames,chords,temperature};
}
function vlq(v){let bytes=[v&127];while(v>>=7)bytes.unshift((v&127)|128);return bytes;}
function u32(n){return[n>>>24&255,n>>>16&255,n>>>8&255,n&255];}
function textBytes(s){return Array.from(new TextEncoder().encode(s));}
function meta(type,s){let b=textBytes(s);return[255,type,...vlq(b.length),...b];}
function track(events){events.sort((a,b)=>a.tick-b.tick||a.order-b.order);let out=[],last=0;for(let event of events){out.push(...vlq(event.tick-last),...event.bytes);last=event.tick;}out.push(0,255,47,0);return[...textBytes('MTrk'),...u32(out.length),...out];}
export function midi(piece){
  const ppq=480,tempo=Math.round(60000000/piece.bpm),end=piece.bars*4*ppq;
  let conductor=track([{tick:0,order:0,bytes:meta(3,piece.title)},
    {tick:0,order:1,bytes:[255,81,3,tempo>>>16&255,tempo>>>8&255,tempo&255]},
    {tick:0,order:2,bytes:[255,88,4,4,2,24,8]},
    {tick:0,order:3,bytes:meta(1,'Cadenza custom neural piano model; newly sampled composition. Seed '+piece.seed)},
    {tick:end,order:0,bytes:[255,1,0]}]);
  const voices=[];
  for(let voice=0;voice<2;voice++){
    const events=[{tick:0,order:0,bytes:meta(3,piece.instrument_names?.[voice]||(voice?'Piano left hand':'Piano right hand'))},{tick:0,order:1,bytes:[192+voice,piece.programs?.[voice]||0]}];
    for(const note of piece.notes.filter(n=>n.voice===voice)){
      let start=Math.round(note.beat*ppq),stop=Math.min(end,Math.max(start+1,Math.round((note.beat+note.duration)*ppq)));
      events.push({tick:start,order:3,bytes:[144+voice,note.pitch,note.velocity]},
                  {tick:stop,order:2,bytes:[128+voice,note.pitch,0]});
    }
    // Lift pedal at each harmony boundary and at the end.
    for(let bar=0;bar<piece.bars;bar++){
      const tick=bar*4*ppq;events.push({tick,order:1,bytes:[176+voice,64,0]},
        {tick:tick+20,order:4,bytes:[176+voice,64,70]},
        {tick:tick+4*ppq-45,order:4,bytes:[176+voice,64,0]});
    }
    events.push({tick:end,order:1,bytes:[176+voice,64,0]},{tick:end,order:2,bytes:[176+voice,123,0]});
    voices.push(track(events));
  }
  return Uint8Array.from([...textBytes('MThd'),0,0,0,6,0,1,0,3,ppq>>>8,ppq&255,...conductor,...voices.flat()]);
}
export function arrange(piece,palette='random'){
  const presets={piano:{programs:[0,0],names:['Acoustic grand piano','Acoustic grand piano'],ranges:[[60,91],[36,59]]},
    violin:{programs:[40,42],names:['Violin','Cello'],ranges:[[55,96],[36,64]]},
    flute:{programs:[73,46],names:['Flute','Harp'],ranges:[[60,86],[36,59]]},
    strings:{programs:[48,48],names:['Upper strings','Lower strings'],ranges:[[55,96],[36,64]]},
    winds:{programs:[71,70],names:['Clarinet','Bassoon'],ranges:[[50,87],[34,67]]}};
  if(palette==='random')palette=Object.keys(presets)[piece.seed%Object.keys(presets).length];
  const preset=presets[palette];if(!preset)throw Error('Unknown instrument palette');
  piece.programs=preset.programs;piece.instrument_names=preset.names;piece.palette=palette;
  for(const n of piece.notes){const [low,high]=preset.ranges[n.voice];while(n.pitch>high)n.pitch-=12;while(n.pitch<low)n.pitch+=12;}
  const active=new Map();for(const n of piece.notes){const key=n.voice+':'+n.pitch,prior=active.get(key);if(prior&&prior.beat+prior.duration>n.beat)prior.duration=Math.max(.001,n.beat-prior.beat-.001);active.set(key,n);}
  return piece;
}
