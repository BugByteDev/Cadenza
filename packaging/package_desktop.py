"""Stage official Node, license/source notices, and a portable desktop archive."""
import os,sys,shutil,subprocess,tarfile,zipfile,urllib.request,json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
runtime=root/'build/runtime';notices=root/'build/notices'
runtime.mkdir(parents=True,exist_ok=True);notices.mkdir(parents=True,exist_ok=True)
node=Path(shutil.which('node'));shutil.copy2(node,runtime/node.name)
version=subprocess.check_output([str(node),'--version'],text=True).strip()
urllib.request.urlretrieve(f'https://raw.githubusercontent.com/nodejs/node/{version}/LICENSE',notices/'Node-LICENSE.txt')
(notices/'SOURCE-LINKS.txt').write_text(f'Node.js {version}: https://nodejs.org/dist/{version}/node-{version}.tar.gz\nPython: https://www.python.org/downloads/source/\nPyInstaller (GPL with distribution exception): https://pyinstaller.org/en/stable/license.html\nPygame 2.6.1 (LGPL): https://github.com/pygame/pygame/tree/2.6.1\nSDL: https://www.libsdl.org/\nTcl/Tk: https://www.tcl.tk/software/tcltk/license.html\nFFmpeg corresponding source is included in this directory.\n')
# Pygame's source includes its SDL build recipes and dependency provenance.
with urllib.request.urlopen('https://pypi.org/pypi/pygame/2.6.1/json') as response:
 info=json.load(response)
source=next(item for item in info['urls'] if item['packagetype']=='sdist')
urllib.request.urlretrieve(source['url'],notices/source['filename'])
for candidate in [Path(sys.base_prefix)/'LICENSE.txt',Path(sys.base_prefix)/'LICENSE']:
 if candidate.exists():shutil.copy2(candidate,notices/'Python-LICENSE.txt');break
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--distpath','build/package','--workpath','build/pyinstaller','packaging/Cadenza.spec'],check=True,cwd=root)
bundle=root/'build/package/Cadenza'
# Windows launcher hides the console but preserves an executable for diagnostics.
if sys.platform=='win32':
 (bundle/'Launch Cadenza.vbs').write_text('Set shell = CreateObject("WScript.Shell")\nshell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)\nshell.Run """" & shell.CurrentDirectory & "\\Cadenza.exe""", 0, False\n')
else:
 (bundle/'cadenza.desktop').write_text('[Desktop Entry]\nType=Application\nName=Cadenza\nComment=Local AI classical composer\nExec=Cadenza\nIcon=cadenza\nTerminal=false\nCategories=AudioVideo;Audio;\n')
 (bundle/'install.sh').write_text('#!/bin/sh\nset -eu\ncd "$(dirname "$0")"\nmkdir -p "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/512x512/apps"\ncp _internal/dist/assets/icon-512.png "$HOME/.local/share/icons/hicolor/512x512/apps/cadenza.png"\nsed "s|Exec=Cadenza|Exec=\\"$(pwd)/Cadenza\\"|" cadenza.desktop > "$HOME/.local/share/applications/cadenza.desktop"\n./Cadenza &\n')
 (bundle/'install.sh').chmod(0o755)
exe=bundle/('Cadenza.exe' if sys.platform=='win32' else 'Cadenza')
subprocess.run([str(exe),'--smoke'],check=True,env={**os.environ,'SDL_AUDIODRIVER':'dummy'})
label=os.environ.get('CADENZA_PACKAGE','desktop')
archive=root/f'build/Cadenza-{label}.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for path in bundle.rglob('*'):
  if path.is_file():z.write(path,path.relative_to(bundle.parent))
print(archive)
