import fs from 'node:fs';
import {BasicMIDI,SoundBankLoader,SpessaSynthProcessor,SpessaSynthSequencer,SpessaLog} from './dist/vendor/synth.mjs';
import {midi} from './dist/engine.mjs';
SpessaLog.setLogLevel(false,false,false);
const piece=JSON.parse(fs.readFileSync(process.argv[2])),rate=44100;
const bank=fs.readFileSync(new URL('./sounds/GeneralUser-GS.sf2',import.meta.url));
const synth=new SpessaSynthProcessor(rate,{eventsEnabled:false});
synth.soundBankManager.addSoundBank(SoundBankLoader.fromArrayBuffer(bank.buffer.slice(bank.byteOffset,bank.byteOffset+bank.byteLength)),'main');
await synth.processorInitialized;
const seq=new SpessaSynthSequencer(synth);const bytes=midi(piece);
seq.loadNewSongList([BasicMIDI.fromArrayBuffer(bytes.buffer)]);seq.play();
const left=new Float32Array(128),right=new Float32Array(128),out=Buffer.alloc(512);const total=Math.round((piece.seconds+2)*rate);
for(let pos=0;pos<total;pos+=128){seq.processTick();const count=Math.min(128,total-pos);synth.process(left,right,0,count);for(let i=0;i<count;i++){out.writeInt16LE(Math.round(Math.max(-1,Math.min(1,left[i]))*32767),i*4);out.writeInt16LE(Math.round(Math.max(-1,Math.min(1,right[i]))*32767),i*4+2);}if(!process.stdout.write(out.subarray(0,count*4)))await new Promise(resolve=>process.stdout.once('drain',resolve));}
