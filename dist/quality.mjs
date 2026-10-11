// Transparent musical heuristics, not a trained listening critic.
// Measures are normalized by note/phrase counts: extra length earns no points.
export function assess(piece){
 const melody=piece.notes.filter(n=>n.voice===0),intervals=melody.slice(1).map((n,i)=>n.pitch-melody[i].pitch);
 const ratio=(xs,p)=>xs.filter(p).length/Math.max(1,xs.length);
 const smoothness=1-ratio(intervals,x=>Math.abs(x)>9);
 const movement=1-ratio(intervals,x=>x===0);
 const range=Math.max(...melody.map(n=>n.pitch))-Math.min(...melody.map(n=>n.pitch));
 const balancedRange=Math.max(0,1-Math.abs(range-17)/22);
 const windows=[];
 for(let beat=0;beat<piece.bars*4;beat+=16){
  const ns=melody.filter(n=>n.beat>=beat&&n.beat<beat+16);
  windows.push({density:ns.length/16,mean:ns.reduce((s,n)=>s+n.pitch,0)/Math.max(1,ns.length)});
 }
 const changes=windows.slice(1).map((w,i)=>Math.abs(w.mean-windows[i].mean));
 const development=ratio(changes,x=>x>=1&&x<=8);
 const density=ratio(windows,w=>w.density>=.65&&w.density<=3.5);
 const roots=new Set(piece.chords.map(c=>c.root)).size;
 const harmony=Math.min(1,roots/5);
 const strong=melody.filter(n=>Math.abs(n.beat%4)<.05);
 const consonance=ratio(strong,n=>{
  const c=piece.chords.filter(c=>c.beat<=n.beat).at(-1);
  return c&&[0,c.quality===1?3:4,c.quality===2?6:7].some(i=>(c.root+i)%12===n.pitch%12);
 });
 const ending=melody.at(-1).pitch%12===piece.tonic&&piece.chords.at(-1).root===piece.tonic?1:0;
 const metrics={smoothness,movement,balancedRange,development,density,harmony,consonance,ending};
 const score=100*(.17*smoothness+.12*movement+.1*balancedRange+.2*development+.1*density+.1*harmony+.13*consonance+.08*ending);
 return {score,metrics};
}
export function selectBest(candidates){
 if(!candidates.length)throw Error('No valid compositions were generated; please try again.');
 return candidates.map(piece=>({piece,...assess(piece)})).sort((a,b)=>b.score-a.score)[0];
}
