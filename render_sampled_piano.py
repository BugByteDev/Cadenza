"""Direct playback of recorded piano samples, with no oscillator or sample loops."""
import array,json,math,struct,subprocess,sys,zipfile,shutil
from pathlib import Path
def render(piece,output,rate=44100):
 bank=Path(__file__).parent/'sounds'/'Salamander-Piano.pcm.zip'
 with zipfile.ZipFile(bank) as z:
  mapping=json.loads(z.read('samples.json'));samples={}
  for entry in mapping:
   pcm=array.array('h');pcm.frombytes(z.read(entry['note']+'.pcm'))
   if sys.byteorder!='little':pcm.byteswap()
   samples[entry['midi_pitch']]=pcm
 total=round((piece['seconds']+2)*rate);mix=array.array('f',[0.])*total;cache={}
 for note in piece['notes']:
  pitch=note['pitch']
  if pitch not in cache:
   root=min(samples,key=lambda p:abs(p-pitch));source=samples[root];ratio=2**((pitch-root)/12)
   shifted=array.array('f')
   for i in range(int((len(source)-1)/ratio)):
    pos=i*ratio;j=int(pos);fraction=pos-j
    shifted.append((source[j]*(1-fraction)+source[j+1]*fraction)/32768)
   cache[pitch]=shifted
  source=cache[pitch];start=round(note['beat']*60/piece['bpm']*rate)
  hold=note['duration']*60/piece['bpm']
  # A short pedal tail, followed by damper release; the recording never loops.
  hold+=.18;release=.65;frames=min(len(source),round((hold+release)*rate),total-start)
  gain=(note['velocity']/100)**1.4*(.8 if note['voice'] else 1.)
  release_start=round(hold*rate);release_frames=max(1,round(release*rate))
  for i in range(frames):
   envelope=1. if i<release_start else max(0.,1-(i-release_start)/release_frames)**2
   mix[start+i]+=source[i]*gain*envelope
 peak=max(abs(v) for v in mix)
 if peak<1e-6:raise RuntimeError('Recorded piano output is silent')
 gain=.85/peak;energy=0.
 encoder=shutil.which('ffmpeg')
 if not encoder:raise RuntimeError('Install FFmpeg to export recorded piano audio')
 process=subprocess.Popen([encoder,'-v','error','-y','-f','s16le','-ar',str(rate),'-ac','1','-i','pipe:0','-ac','2','-c:a','aac','-b:a','128k',str(output)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
 try:
  for start in range(0,total,4096):
   pcm=array.array('h')
   for v in mix[start:start+4096]:energy+=(v*gain)**2;pcm.append(round(v*gain*32767))
   if sys.byteorder!='little':pcm.byteswap()
   process.stdin.write(pcm.tobytes())
  process.stdin.close();error=process.stderr.read().decode();code=process.wait()
  if code:raise RuntimeError(error)
 finally:
  if process.poll() is None:process.kill();process.wait()
 return {'sound_bank':bank.name,'instrument':'Recorded Yamaha C5 grand piano, Alexander Holm','sample_rate':rate,'seconds':total/rate,'normalized_peak':.85,'rms':math.sqrt(energy/total),'file_bytes':Path(output).stat().st_size,'loops':False,'max_pitch_shift_semitones':max(abs(p-min(samples,key=lambda k:abs(k-p))) for p in cache)}
