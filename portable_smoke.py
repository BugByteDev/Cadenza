"""Small OS-independent smoke checks; full audio checks need FFmpeg locally."""
import json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as temp:
 piece={'bpm':90,'bars':1,'seconds':3,'title':'Compatibility check','seed':1,'programs':[40,42],'notes':[{'beat':0,'duration':2,'pitch':72,'velocity':80,'voice':0},{'beat':0,'duration':2,'pitch':48,'velocity':70,'voice':1}]}
 source=Path(temp)/'piece.json';source.write_text(json.dumps(piece))
 result=subprocess.run(['node',str(ROOT/'render_soundfont.mjs'),str(source)],capture_output=True,check=True)
 assert len(result.stdout)==44100*5*4
 assert max(result.stdout)>0
print('Portable SoundFont render passed')
