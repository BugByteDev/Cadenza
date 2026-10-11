"""Build a compact, non-looping PCM sample archive from licensed real recordings."""
import array,hashlib,json,struct,subprocess,urllib.request
from pathlib import Path
OUT=Path(__file__).parent/'sounds'
def chunk(name,data):
 return name.encode()+struct.pack('<I',len(data))+data+(b'\0' if len(data)%2 else b'')
def listing(kind,items):return chunk('LIST',kind.encode()+b''.join(items))
def name(s):return s.encode()[:20].ljust(20,b'\0')
def gen(op,value):return struct.pack('<HH',op,value&65535)
def main():
 OUT.mkdir(exist_ok=True);pcm=bytearray();headers=[];zones=[];records=[]
 keys=[(note+str(octave),12*(octave+1)+offset) for octave in range(2,7) for note,offset in [('C',0),('Ds',3),('Fs',6),('A',9)]]+[('C7',96)]
 for i,(label,pitch) in enumerate(keys):
  url='https://tonejs.github.io/audio/salamander/'+label+'.mp3'
  data=urllib.request.urlopen(url,timeout=40).read()
  decoded=subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-i','pipe:0','-t','8','-f','s16le','-ac','1','-ar','44100','pipe:1'],input=data,capture_output=True,check=True).stdout
  samples=array.array('h');samples.frombytes(decoded)
  # Fade only the file boundary, retaining the recording's real attack/decay.
  fade=min(6615,len(samples))
  for j in range(fade):samples[-fade+j]=round(samples[-fade+j]*(fade-j)/fade)
  start=len(pcm)//2;end=start+len(samples);pcm.extend(samples.tobytes());pcm.extend(b'\0'*92)
  headers.append(struct.pack('<20sIIIIIBbHH',name(label),start,end,start,end,44100,pitch,0,0,1))
  low=0 if i==0 else (keys[i-1][1]+pitch)//2+1
  high=127 if i==len(keys)-1 else (pitch+keys[i+1][1])//2
  zones.append(gen(43,low|(high<<8))+gen(34,-12000)+gen(38,-600)+gen(54,0)+gen(58,pitch)+gen(53,i))
  records.append({'note':label,'midi_pitch':pitch,'source':url,'source_sha256':hashlib.sha256(data).hexdigest(),'sample_frames':len(samples),'key_range':[low,high]})
  print('Recorded sample',label,flush=True)
 import zipfile
 bank_path=OUT/'Salamander-Piano.pcm.zip'
 with zipfile.ZipFile(bank_path,'w',zipfile.ZIP_DEFLATED) as archive:
  for record,header in zip(records,headers):
   fields=struct.unpack('<20sIIIIIBbHH',header)
   archive.writestr(record['note']+'.pcm',pcm[fields[1]*2:fields[2]*2])
  archive.writestr('samples.json',json.dumps(records))
 bank=bank_path.read_bytes()
 license=urllib.request.urlopen('https://raw.githubusercontent.com/sfzinstruments/SalamanderGrandPiano/master/LICENSE').read()
 (OUT/'Salamander-LICENSE.txt').write_bytes(license)
 (OUT/'Salamander-Piano.asset.json').write_text(json.dumps({'author':'Alexander Holm','instrument':'Yamaha C5 grand piano','license':'CC BY 3.0','license_url':'https://creativecommons.org/licenses/by/3.0/','collection_readme':'https://raw.githubusercontent.com/Tonejs/audio/master/salamander/README','adaptations':'MP3 decoded to 44.1 kHz mono, limited to eight seconds with boundary fade, played directly without sample loops. Single sampled velocity layer.','bank_sha256':hashlib.sha256(bank).hexdigest(),'records':records},indent=2))
 print('Built',len(bank),'byte real piano bank')
if __name__=='__main__':main()
