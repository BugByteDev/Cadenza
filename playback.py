"""Decode AAC with our bundled encoder and play PCM through SDL."""
import subprocess,tempfile,time
from pathlib import Path
from runtime import executable,process_options

def play(path):
 import pygame
 with tempfile.TemporaryDirectory(prefix='cadenza-play-') as temp:
  wav=Path(temp)/'preview.wav'
  subprocess.run([executable('ffmpeg'),'-v','error','-y','-i',str(path),str(wav)],check=True,**process_options())
  pygame.mixer.init(frequency=44100)
  try:
   pygame.mixer.music.load(str(wav));pygame.mixer.music.play()
   while pygame.mixer.music.get_busy():time.sleep(.05)
  finally:pygame.mixer.quit()
