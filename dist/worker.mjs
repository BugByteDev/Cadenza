import {NeuralPiano,compose,midi,arrange,random} from './engine.mjs';
import {selectBest} from './quality.mjs';
import {NeuralNamer} from './titles.mjs';
let net,hashes,namer;
self.onmessage=async({data})=>{
  try{
    if(!net){
      self.postMessage({type:'status',message:'Loading the trained piano model…'});
      const [modelResponse,noveltyResponse,titleResponse]=await Promise.all([fetch('./model.json'),fetch('./novelty.bin'),fetch('./title-model.json')]);
      if(!modelResponse.ok||!noveltyResponse.ok||!titleResponse.ok)throw Error('The trained models are unavailable. Please try again later.');
      net=new NeuralPiano(await modelResponse.json());hashes=new Uint32Array(await noveltyResponse.arrayBuffer());
      namer=new NeuralNamer(await titleResponse.json());
    }
    let palette=data?.palette||'random';
    if(palette==='random')palette=['piano','violin','flute','strings','winds'][crypto.getRandomValues(new Uint32Array(1))[0]%5];
    const families={piano:[],violin:['violin','cello'],flute:['flute','harp'],strings:['strings','cello'],winds:['clarinet','bassoon']};
    const models=await Promise.all(families[palette].map(async f=>{const r=await fetch('./instruments/'+f+'/model.json');return r.ok?new NeuralPiano(await r.json()):null;}));
    const candidates=[];let error;
    for(let attempt=0;attempt<14&&candidates.length<8;attempt++){
      self.postMessage({type:'status',message:`Developing and comparing compositions… ${candidates.length}/8 ready`});
      const seed=crypto.getRandomValues(new Uint32Array(1))[0];
      try{candidates.push(arrange(compose(models[0]||net,hashes,seed,null,{developed:true,deferTitle:true,bassNet:models[1]||net}),palette));}
      catch(e){error=e;if(!e.message.includes('fragment'))throw e;}
    }
    if(!candidates.length)throw error;
    const selected=selectBest(candidates),piece=selected.piece;
    piece.title=namer.generate(random(piece.seed^0x517cc1b7));
    piece.selection={candidates:candidates.length,score:selected.score,metrics:selected.metrics};
    arrange(piece,palette);
    const bytes=midi(piece);self.postMessage({type:'result',piece,bytes,report:net.report,titleReport:namer.report},[bytes.buffer]);
  }catch(e){self.postMessage({type:'error',message:e.message});}
};
