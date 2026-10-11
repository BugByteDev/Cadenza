// Separate trained word-level neural model. No complete output titles are stored.
function hash(words){let h=2166136261;for(const b of new TextEncoder().encode(words.join(' ')))h=Math.imul(h^b,16777619)>>>0;return h;}
const STOP=new Set('a an the of to and or but for from by with at on in into as is was are were my your our their his her its than if that which whose when where while'.split(' '));
const AVOID=new Set('bee robin spirit heaven to it me be been being not see so then now yes no us them i you he she we they thou thee thy thine hath doth tis t unto upon never nobody somebody myself yourself himself herself ourselves themselves'.split(' '));
// A vocabulary constraint keeps musical titles focused; phrases remain neural samples.
const THEME=new Set('morning evening night midnight dawn dusk day sun moon star stars sky heaven cloud clouds wind winds breeze storm rain snow frost winter summer autumn spring sea ocean shore river brook stream lake water wave waves tide mountain mountains hill hills valley meadow field fields forest woods wood garden flower flowers rose roses lily lilies violet bird birds robin bee butterfly grass leaf leaves tree trees light shadow shadows silence quiet still rest dream dreams sleep memory memories spirit soul hope love joy sorrow heart golden silver blue purple white dark deep distant gentle soft wild bright eternal lonely silent before after beyond beneath under over through between above below near far again away'.split(' '));
const ADJECTIVE=new Set('quiet still golden silver blue purple white dark deep distant gentle soft wild bright eternal lonely silent'.split(' '));
const PREPOSITION=new Set('before after beyond beneath under over through between above below near in of'.split(' '));
const NOUN=new Set([...THEME].filter(w=>!ADJECTIVE.has(w)&&!PREPOSITION.has(w)&&!['far','again','away'].includes(w)));
export class NeuralNamer{
  constructor(model){this.vocab=model.vocabulary;this.report=model.report;this.training=new Set(model.training_hashes);this.used=new Set();this.wordUse=new Map();this.weights={};for(const[k,v]of Object.entries(model.weights))this.weights[k]={shape:v.shape,values:Float32Array.from(v.values)};}
  predict(context){const w=this.weights,e=w.e,dimension=e.shape[1],hidden=w.b1.shape[0];let h=Float64Array.from(w.b1.values);
    for(let position=0;position<4;position++)for(let i=0;i<dimension;i++){const value=e.values[context[position]*dimension+i],offset=(position*dimension+i)*hidden;for(let j=0;j<hidden;j++)h[j]+=value*w.w1.values[offset+j];}
    for(let i=0;i<hidden;i++)h[i]=Math.tanh(h[i]);let z=Float64Array.from(w.b2.values);
    for(let i=0;i<hidden;i++){const offset=i*z.length;for(let j=0;j<z.length;j++)z[j]+=h[i]*w.w2.values[offset+j];}return z;
  }
  generate(rng){let candidates=[];
    for(let attempt=0;attempt<96;attempt++){
      let context=[0,0,0,1],words=[],score=0,finished=false;
      for(let position=0;position<8;position++){
        let logits=this.predict(context),max=Math.max(...logits),temperature=position===0?2.0:1.05,weights=Array.from(logits,(v,i)=>{
          const word=this.vocab[i];if(i<2||AVOID.has(word))return 0;
          const prior=words.at(-1);
          if(i>2){
            if(position===0&&!NOUN.has(word)&&!ADJECTIVE.has(word)&&!PREPOSITION.has(word))return 0;
            if(position>0){
              if(ADJECTIVE.has(prior)&&!NOUN.has(word))return 0;
              if(PREPOSITION.has(prior)&&word!=='the'&&!NOUN.has(word)&&!ADJECTIVE.has(word))return 0;
              if(prior==='the'&&!NOUN.has(word)&&!ADJECTIVE.has(word))return 0;
              if(NOUN.has(prior)&&(!PREPOSITION.has(word)||word==='of'||words.some(w=>PREPOSITION.has(w))))return 0;
            }
          }
          if(i===2&&!NOUN.has(prior))return 0;
          if(i>2&&!STOP.has(word)&&!THEME.has(word))return 0;
          if(i===2)return position<2?0:Math.exp((v-max)/temperature)*(position>=5?2:1);
          if(position===0&&STOP.has(word))return 0;
          if(position===0&&['spirit','morning','day'].includes(word))return 0;
          if(words.includes(word)&&!STOP.has(word))return 0;
          return Math.exp((v-max)/temperature)*(position===0&&ADJECTIVE.has(word)?6:1)/(1+(this.wordUse.get(word)||0)*.5);
        });
        // Sample from a bounded high-probability set instead of rare word noise.
        const top=weights.map((w,i)=>[w,i]).sort((a,b)=>b[0]-a[0]).slice(0,position===0?60:24);
        let total=top.reduce((s,[w])=>s+w,0),draw=rng()*total,token=top[0][1];
        for(const[w,i]of top){draw-=w;if(draw<=0){token=i;break;}}
        score+=Math.log(Math.max(1e-12,weights[token]/Math.max(1e-12,weights.reduce((a,b)=>a+b,0))));
        if(token===2){finished=true;break;}words.push(this.vocab[token]);context=[...context.slice(1),token];
      }
      if(!finished||words.length<2||words.length>7||STOP.has(words.at(-1))||this.training.has(hash(words)))continue;
      const lower=words.join(' ');if(this.used.has(lower)||lower.includes('of the')||words.length>5)continue;
      // Prefer concise names and complete nominal or poetic phrases.
      if(words.some(w=>['is','was','are','were','will','would','could','should','must','did','do','does','have','has','had','am'].includes(w)))continue;
      const penalty=words.filter(w=>['will','would','could','should','must','did','do','does','have','has','had','am'].includes(w)).length*.8;
      candidates.push({words,score:score/(words.length+1)-penalty-.035*words.length});
    }
    if(!candidates.length)throw Error('Title model needs another sampling attempt');
    candidates.sort((a,b)=>b.score-a.score);const best=candidates[Math.floor(rng()*Math.min(24,candidates.length))];
    const lower=best.words.join(' ');this.used.add(lower);for(const word of best.words)if(!STOP.has(word))this.wordUse.set(word,(this.wordUse.get(word)||0)+1);
    return best.words.map((word,i)=>i&&STOP.has(word)?word:word[0].toUpperCase()+word.slice(1)).join(' ');
  }
}
