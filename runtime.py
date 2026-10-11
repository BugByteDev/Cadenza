"""Installed-runtime discovery and writable app data across desktop platforms."""
import os,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def executable(name):
    bundled=ROOT/'runtime'/(name+'.exe' if sys.platform=='win32' else name)
    if bundled.is_file():return str(bundled)
    found=shutil.which(name)
    if found:return found
    for directory in ['/opt/homebrew/bin','/usr/local/bin']:
        candidate=Path(directory)/name
        if candidate.exists():return str(candidate)
    raise RuntimeError(f'Install {name}, add it to PATH, and reopen Cadenza.')

def data_dir():
    override=os.environ.get('CADENZA_DATA_DIR')
    if override:folder=Path(override)
    elif sys.platform=='win32':folder=Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))/'Cadenza/generated'
    elif sys.platform=='darwin':folder=Path.home()/'Library/Application Support/Cadenza/generated'
    else:folder=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'Cadenza/generated'
    folder.mkdir(parents=True,exist_ok=True);return folder


def child_command(mode, *args):
    if getattr(sys, 'frozen', False):return [sys.executable, mode, *map(str,args)]
    return [sys.executable, str(ROOT/'desktop.py'), mode, *map(str,args)]
