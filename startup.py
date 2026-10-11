"""Desktop dependency checks and a guided setup dialog."""
import importlib.util,json,subprocess,sys,webbrowser
from pathlib import Path
from runtime import ROOT,executable,process_options
DEPENDENCIES=[('Node.js 22+','https://nodejs.org/en/download'),('FFmpeg with AAC support','https://ffmpeg.org/download.html'),('Pygame 2.6.1','https://www.pygame.org/wiki/GettingStarted')]
def missing_dependencies():
 missing=[]
 if sys.version_info<(3,11):missing.append(('Python 3.11+','https://www.python.org/downloads/'))
 if importlib.util.find_spec('tkinter') is None:missing.append(('Python Tk support','https://www.python.org/downloads/'))
 for name,url in DEPENDENCIES[:2]:
  try:
   binary=executable('node' if name.startswith('Node') else 'ffmpeg')
   result=subprocess.run([binary,'--version' if name.startswith('Node') else '-version'],capture_output=True,text=True,timeout=15,**process_options())
   if result.returncode:raise RuntimeError()
   if name.startswith('Node') and int(result.stdout.strip().lstrip('v').split('.')[0])<22:raise RuntimeError()
  except (RuntimeError,OSError,ValueError,subprocess.TimeoutExpired):missing.append((name,url))
 if importlib.util.find_spec('pygame') is None:missing.append(DEPENDENCIES[2])
 return missing

def preflight():
 missing=missing_dependencies()
 if not missing:return True
 instructions='Cadenza needs:\n'+ '\n'.join('• '+name for name,_ in missing)+'\n\n'+(ROOT/'DEPENDENCIES.txt').read_text()
 try:
  import tkinter as tk
  from tkinter import messagebox
  window=tk.Tk();window.title('Set up Cadenza');window.geometry('660x510')
  tk.Label(window,text='Install the missing dependencies',font=('',18,'bold')).pack(pady=16)
  text=tk.Text(window,wrap='word',height=17);text.insert('1.0',instructions);text.config(state='disabled');text.pack(fill='both',expand=True,padx=18)
  buttons=tk.Frame(window);buttons.pack(pady=16)
  def install():
   if getattr(sys,'frozen',False):
    messagebox.showinfo('Repair Cadenza','Download and reinstall the complete desktop package. Its runtimes are included.');webbrowser.open('https://github.com/BugByteDev/Cadenza/releases/latest');return
   for name,url in missing:
    if name.startswith('Pygame'):
     if messagebox.askyesno('Install Pygame','Install Pygame in this Python environment now?'):
      result=subprocess.run([sys.executable,'-m','pip','install','pygame==2.6.1'],capture_output=True,text=True,**process_options())
      messagebox.showinfo('Pygame setup','Installed. Click Check again.' if result.returncode==0 else result.stderr[-2000:])
    else:webbrowser.open(url)
  def retry():
   if not missing_dependencies():window.destroy()
   else:messagebox.showinfo('Setup incomplete','Dependencies are still missing. Finish installing them, then reopen Cadenza so PATH changes take effect.')
  tk.Button(buttons,text='Install / repair',command=install).pack(side='left',padx=6)
  tk.Button(buttons,text='Check again',command=retry).pack(side='left',padx=6)
  tk.Button(buttons,text='Close',command=window.destroy).pack(side='left',padx=6)
  window.mainloop()
 except ImportError:
  print(instructions,file=sys.stderr)
  # Python without Tk cannot display the app's setup window; use an OS dialog.
  if sys.platform=='win32':
   import ctypes
   if ctypes.windll.user32.MessageBoxW(0,instructions,'Install Cadenza dependencies',1)==1:webbrowser.open('https://www.python.org/downloads/')
  elif sys.platform=='darwin':
   subprocess.run(['osascript','-e','display dialog '+json.dumps(instructions)+' buttons {"Close", "Install Python"} default button "Install Python"'],capture_output=True)
   webbrowser.open('https://www.python.org/downloads/')
  else:
   try:subprocess.run(['zenity','--error','--title=Cadenza setup','--text='+instructions],**process_options())
   except FileNotFoundError:pass
  return False
 return not missing_dependencies()
