"""Cross-platform sampled audio rendering. Piano recordings or bundled SF2 engine."""
import json,shutil,subprocess,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def render(piece,output,rate=44100):
    if all(p==0 for p in piece.get('programs',[0,0])):
        from render_sampled_piano import render as piano
        return piano(piece,output,rate)
    node=shutil.which('node');encoder=shutil.which('ffmpeg')
    if not node or not encoder:raise RuntimeError('Install Node.js and FFmpeg, then reopen Cadenza.')
    with tempfile.TemporaryDirectory(prefix='cadenza-') as temp:
        source=Path(temp)/'piece.json';source.write_text(json.dumps(piece))
        errors=Path(temp)/'synth.log'
        with errors.open('wb') as log:
            synth=subprocess.Popen([node,str(ROOT/'render_soundfont.mjs'),str(source)],stdout=subprocess.PIPE,stderr=log)
            try:
                encode=subprocess.Popen([encoder,'-v','error','-y','-f','s16le','-ar',str(rate),'-ac','2','-i','pipe:0','-c:a','aac','-b:a','128k',str(output)],stdin=synth.stdout,stderr=subprocess.PIPE)
                synth.stdout.close();_,error=encode.communicate();code=synth.wait()
                if code or encode.returncode:raise RuntimeError(errors.read_text(errors='replace')[-800:]+error.decode(errors='replace'))
            finally:
                if synth.poll() is None:synth.terminate();synth.wait()
    if Path(output).stat().st_size<1000:raise RuntimeError('Audio render was empty')
    return {'sound_bank':'GeneralUser-GS.sf2','seconds':piece['seconds']+2,'sample_rate':rate,'file_bytes':Path(output).stat().st_size}
if __name__=='__main__':print(json.dumps(render(json.loads(Path(sys.argv[1]).read_text()),Path(sys.argv[2]))))
