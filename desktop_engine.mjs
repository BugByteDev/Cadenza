import fs from 'node:fs';import crypto from 'node:crypto';import {fileURLToPath} from 'node:url';
import {NeuralPiano,compose,midi,arrange,random} from './dist/engine.mjs';
import {NeuralNamer} from './dist/titles.mjs';import {selectBest} from './dist/quality.mjs';
const root=fileURLToPath(new URL('.',import.meta.url)),request=JSON.parse(fs.readFileSync(0,'utf8'));
const load=name=>JSON.parse(fs.readFileSync(root+'dist/'+name)),base=new NeuralPiano(load('model.json'));
let palette=request.palette||'random';
if(palette==='random')palette=['piano','violin','flute','strings','winds'][crypto.randomInt(5)];
const families={violin:['violin','cello'],flute:['flute','harp'],strings:['strings','cello'],winds:['clarinet','bassoon'],piano:[]};
const specialists=(families[palette]||[]).map(f=>{try{return new NeuralPiano(load('instruments/'+f+'/model.json'));}catch(e){if(e.code==='ENOENT')return null;throw e;}});
const sources=['novelty.bin',...(families[palette]||[]).map(f=>'instruments/'+f+'/novelty.bin')],allHashes=new Set();
for(const source of sources){try{const b=fs.readFileSync(root+'dist/'+source);for(const h of new Uint32Array(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)))allHashes.add(h);}catch(e){if(source==='novelty.bin')throw e;}}
const hashes=Uint32Array.from([...allHashes].sort((a,b)=>a-b)),candidates=[];
for(let attempt=0;attempt<20&&candidates.length<8;attempt++){
 process.stderr.write(JSON.stringify({status:'Developing compositions · '+candidates.length+'/8'})+'\n');
 try{candidates.push(arrange(compose(specialists[0]||base,hashes,crypto.randomInt(0x100000000),null,{developed:true,deferTitle:true,bassNet:specialists[1]||base}),palette));}
 catch(e){if(!e.message.includes('fragment'))throw e;}
}
const selected=selectBest(candidates),piece=selected.piece,namer=new NeuralNamer(load('title-model.json'));
piece.title=namer.generate(random(piece.seed^0x517cc1b7));
piece.selection={candidates:candidates.length,score:selected.score,metrics:selected.metrics};
piece.specialists=(families[palette]||[]).filter((f,i)=>specialists[i]);
arrange(piece,palette);process.stdout.write(JSON.stringify({piece,midi:Buffer.from(midi(piece)).toString('base64')}));
