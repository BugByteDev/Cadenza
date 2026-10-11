"""Verify actual bundled executable and audio resources including native GUI startup."""
import json,subprocess,tempfile,struct,wave
from pathlib import Path
from runtime import ROOT,executable,child_command
from render_portable import render

def check():
 from desktop import Cadenza
 app=Cadenza();app.root.update();app.close()
 result=subprocess.run([executable('node'),str(ROOT/'desktop_engine.mjs')],input=json.dumps({'palette':'piano'}),capture_output=True,text=True,check=True)
 generated=json.loads(result.stdout)
 assert generated['piece']['notes'] and generated['midi'].startswith('TVRoZA'), 'Bundled model/MIDI failed'
 subprocess.run([executable('node'),'--version'],check=True)
 subprocess.run([executable('ffmpeg'),'-version'],check=True,stdout=subprocess.DEVNULL)
 # Both sampled piano and orchestral SoundFont paths must encode and decode.
 with tempfile.TemporaryDirectory() as temp:
  for program in [0,73]:
   piece={'bars':1,'title':'Packaged compatibility check','seed':1,'programs':[program,program],'seconds':2,'bpm':100,'notes':[{'pitch':72,'beat':0,'duration':1,'velocity':85,'voice':0},{'pitch':48,'beat':0,'duration':2,'velocity':70,'voice':1}]}
   output=Path(temp)/f'{program}.m4a'
   source=Path(temp)/f'{program}.json';source.write_text(json.dumps(piece))
   subprocess.run(child_command('--render',source,output),check=True,capture_output=True,text=True)
   result=subprocess.run([executable('ffmpeg'),'-v','error','-i',str(output),'-f','s16le','-ac','1','pipe:1'],check=True,stdout=subprocess.PIPE)
   assert len(result.stdout)>10000 and any(result.stdout), 'Silent or missing PCM'
  import pygame
  pygame.mixer.init();pygame.mixer.quit()
 print('Bundled Node, instruments, M4A encoder/decoder and SDL audio passed')
