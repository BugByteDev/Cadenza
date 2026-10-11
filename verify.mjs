import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {NeuralPiano,compose,midi,arrange} from './dist/engine.mjs';
import {NeuralNamer} from './dist/titles.mjs';
const titleModel=JSON.parse(fs.readFileSync(new URL('./dist/title-model.json',import.meta.url)));
const model=JSON.parse(fs.readFileSync(new URL('./dist/model.json',import.meta.url)));
const net=new NeuralPiano(model),raw=fs.readFileSync(new URL('./dist/novelty.bin',import.meta.url));
const hashes=new Uint32Array(raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength));
for(let i=0;i<6;i++)assert(model.report.test_loss[i]<model.report.test_unconditional_baseline[i]);
const fingerprints=new Set(),results=[];let rejected=0;
for(let seed=12000;results.length<30&&seed<12100;seed++){
  let piece;try{piece=compose(net,hashes,seed,new NeuralNamer(titleModel));}catch(e){if(e.message.includes('fragment')){rejected++;continue;}throw e;}
  const bytes=midi(piece);
  assert.equal(Buffer.from(bytes.slice(0,4)).toString(),'MThd');
  assert.equal(bytes[11],3);assert(piece.notes.length>100);
  const sounding=new Map();
  for(const n of piece.notes){
    assert(Number.isFinite(n.beat)&&n.beat>=0);assert(n.duration>0);assert(n.velocity>0&&n.velocity<=127);
    assert(n.pitch>=36&&n.pitch<=91);assert(n.beat+n.duration<=piece.bars*4+.001);
    const key=n.voice+':'+n.pitch,prior=sounding.get(key);
    if(prior)assert(prior.beat+prior.duration<=n.beat+.001,'same-key overlap');
    sounding.set(key,n);
  }
  const hash=crypto.createHash('sha256').update(bytes).digest('hex');assert(!fingerprints.has(hash));fingerprints.add(hash);
  assert.deepEqual(midi(compose(net,hashes,seed,new NeuralNamer(titleModel))),bytes,'seed reproducibility');
  results.push({seed,title:piece.title,notes:piece.notes.length,sha256:hash});
  if(results.length===1){fs.writeFileSync(new URL('./sample.mid',import.meta.url),bytes);fs.writeFileSync(new URL('./sample.json',import.meta.url),JSON.stringify(piece));}
}
assert.equal(results.length,30,'thirty accepted compositions');
const verification={unique_valid_generations:results.length,rejected_fragment_matches:rejected,all_heads_beat_baseline:true,seed_reproducibility:true,
  checks:['MIDI header/track count','finite durations and positions','piano range','note reattack lifetimes','unique bytes','partial training fingerprint screening'],
  results};
fs.writeFileSync(new URL('./verification.json',import.meta.url),JSON.stringify(verification,null,2));
const sample=JSON.parse(fs.readFileSync(new URL('./sample.json',import.meta.url)));
const expected={piano:[0,0],violin:[40,42],flute:[73,46],strings:[48,48],winds:[71,70]};
for(const [palette,programs]of Object.entries(expected)){
  const p=arrange(structuredClone(sample),palette);assert.deepEqual(p.programs,programs);
  const bytes=midi(p);for(let voice=0;voice<2;voice++)assert(Buffer.from(bytes).includes(Buffer.from([192+voice,programs[voice]])));
}
console.log(JSON.stringify({generations:results.length,rejected_fragment_matches:rejected,all_heads_beat_baseline:true,seed_reproducibility:true}));
