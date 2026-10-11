import {BasicMIDI,SoundBankLoader,SpessaSynthProcessor,SpessaSynthSequencer,SpessaLog,audioToWav} from './vendor/synth.mjs';
import {unzipSync} from './vendor/zip.mjs';
SpessaLog.setLogLevel(false,false,false);
let piano,bank;
const rate=22050;
async function get(url){const r=await fetch(url);if(!r.ok)throw Error('Instrument recordings are unavailable.');return r.arrayBuffer();}
self.onmessage=async({data})=>{try{
 const {piece,bytes}=data,total=Math.ceil((piece.seconds+2)*rate);const left=new Float32Array(total),right=new Float32Array(total);
 if(piece.programs.every(p=>p===0)){
  if(!piano){const archive=unzipSync(new Uint8Array(await get('./sounds/Salamander-Piano.pcm.zip')));const map=JSON.parse(new TextDecoder().decode(archive['samples.json']));piano=map.map(e=>({pitch:e.midi_pitch,pcm:new Int16Array(archive[e.note+'.pcm'].buffer.slice(archive[e.note+'.pcm'].byteOffset,archive[e.note+'.pcm'].byteOffset+archive[e.note+'.pcm'].byteLength))}));}
  for(let n=0;n<piece.notes.length;n++){const note=piece.notes[n];const sample=piano.reduce((a,b)=>Math.abs(a.pitch-note.pitch)<Math.abs(b.pitch-note.pitch)?a:b);const ratio=2**((note.pitch-sample.pitch)/12)*44100/rate;const start=Math.round(note.beat*60/piece.bpm*rate),hold=note.duration*60/piece.bpm+.18;const frames=Math.min(Math.floor((sample.pcm.length-1)/ratio),Math.round((hold+.65)*rate),total-start);const gain=(note.velocity/100)**1.4*(note.voice?.8:1);
   for(let i=0;i<frames;i++){const pos=i*ratio,j=Math.floor(pos),f=pos-j;const env=i<hold*rate?1:Math.max(0,1-(i/rate-hold)/.65)**2;const value=(sample.pcm[j]*(1-f)+sample.pcm[j+1]*f)/32768*gain*env;left[start+i]+=value;right[start+i]+=value;}
  }
 }else{
  if(!bank)bank=SoundBankLoader.fromArrayBuffer(await get('./sounds/GeneralUser-GS.sf2'));
  const synth=new SpessaSynthProcessor(rate,{eventsEnabled:false});synth.soundBankManager.addSoundBank(bank,'main');await synth.processorInitialized;
  const seq=new SpessaSynthSequencer(synth);seq.loadNewSongList([BasicMIDI.fromArrayBuffer(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength))]);seq.play();
  for(let p=0;p<total;p+=128){seq.processTick();synth.process(left,right,p,Math.min(128,total-p));}
 }
 let peak=0;for(let i=0;i<total;i++)peak=Math.max(peak,Math.abs(left[i]),Math.abs(right[i]));if(peak<1e-7)throw Error('Audio was silent.');for(let i=0;i<total;i++){left[i]*=.85/peak;right[i]*=.85/peak;}
 const wav=audioToWav([left,right],rate);self.postMessage({type:'audio',wav},[wav]);
}catch(e){self.postMessage({type:'error',message:e.message});}};
