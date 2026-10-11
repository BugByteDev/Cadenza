"""Native Python desktop UI; local neural engine, no browser or server."""
import sys
if __name__ == "__main__" and len(sys.argv) == 1:
 from startup import preflight
 if not preflight():sys.exit(1)
import base64,json,queue,shutil,subprocess,threading,os,tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from runtime import data_dir, executable, child_command,process_options
ROOT=Path(__file__).resolve().parent
BG='#101a20';FG='#edf0e7';ACCENT='#c6e7ae';MUTED='#96a8aa';PANEL='#19262d'
PALETTES={'Grand piano':'piano','Violin & cello':'violin','Flute & harp':'flute','String ensemble':'strings','Clarinet & bassoon':'winds','Surprise me':'random'}
class Cadenza:
 def __init__(self):
  self.root=tk.Tk();self.root.title('Cadenza');self.root.geometry(os.environ.get('CADENZA_WINDOW_SIZE','1100x760'));self.root.minsize(620,480);self.root.configure(bg=BG)
  self.events=queue.Queue();self.player=None;self.piece=None;self.paths={};self.busy=False;self.closed=False;self.engine_process=None;self.render_process=None
  self.root.protocol('WM_DELETE_WINDOW',self.close)
  icon=ROOT/'dist/assets/icon-128.png'
  if icon.exists():self.icon=tk.PhotoImage(file=str(icon));self.root.iconphoto(True,self.icon)
  style=ttk.Style();style.theme_use('clam')
  style.configure('Primary.TButton',background=ACCENT,foreground=BG,font=('Helvetica',13,'bold'),padding=(20,12),borderwidth=0)
  style.map('Primary.TButton',background=[('active','#d9efc9'),('disabled','#35484b')],foreground=[('disabled','#8b9b9e')])
  style.configure('Soft.TButton',background='#263943',foreground=FG,font=('Helvetica',11),padding=(16,10),borderwidth=0)
  style.map('Soft.TButton',background=[('active','#354c57')],foreground=[('disabled','#667a82')])
  style.configure('TCombobox',fieldbackground='#263943',background='#263943',foreground=FG,arrowcolor=ACCENT,padding=8)
  style.map('TCombobox',fieldbackground=[('readonly','#263943')],foreground=[('readonly',FG)])
  style.configure('TProgressbar',background=ACCENT,troughcolor=PANEL,bordercolor=PANEL,lightcolor=PANEL,darkcolor=PANEL,borderwidth=0)
  style.configure('Treeview',bordercolor=BG,lightcolor=BG,darkcolor=BG,background=BG,fieldbackground=BG,foreground=MUTED,rowheight=38,font=('Helvetica',11),borderwidth=0)
  style.map('Treeview',background=[('selected','#263943')],foreground=[('selected',FG)])
  sidebar=tk.Frame(self.root,bg=BG,width=210,padx=22,pady=28);sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
  tk.Label(sidebar,text='cadenza',font=('Georgia',27),fg=FG,bg=BG).pack(anchor='w')
  tk.Label(sidebar,text='YOUR COMPOSING ROOM',wraplength=130,justify='left',font=('Helvetica',8),fg=MUTED,bg=BG).pack(anchor='w',pady=(8,30))
  tk.Label(sidebar,text='SAVED COMPOSITIONS',wraplength=130,justify='left',font=('Helvetica',8,'bold'),fg=ACCENT,bg=BG).pack(anchor='w',pady=(0,10))
  self.library=ttk.Treeview(sidebar,show='tree',selectmode='browse');self.library.pack(fill='both',expand=True);self.library.bind('<<TreeviewSelect>>',self.restore)
  ttk.Button(sidebar,text='About the models',style='Soft.TButton',command=self.about).pack(fill='x',pady=(20,8))
  tk.Label(sidebar,text='Private. Local. Original.',font=('Helvetica',10),fg=MUTED,bg=BG).pack(anchor='w')
  self.sidebar=sidebar
  viewport=tk.Frame(self.root,bg=PANEL);viewport.pack(side='left',fill='both',expand=True)
  self.scroll= tk.Canvas(viewport,bg=PANEL,highlightthickness=0)
  scrollbar=ttk.Scrollbar(viewport,orient='vertical',command=self.scroll.yview);scrollbar.pack(side='right',fill='y')
  self.scroll.configure(yscrollcommand=scrollbar.set);self.scroll.pack(side='left',fill='both',expand=True)
  body=tk.Frame(self.scroll,bg=PANEL,padx=28,pady=24)
  self.body=body;self.body_window=self.scroll.create_window(0,0,window=body,anchor='nw')
  body.bind('<Configure>',lambda e:self.scroll.configure(scrollregion=self.scroll.bbox('all')))
  self.scroll.bind('<Configure>',self.resize)
  self.root.bind_all('<MouseWheel>',self.wheel)
  self.root.bind_all('<Button-4>',lambda e:self.wheel(e,-1))
  self.root.bind_all('<Button-5>',lambda e:self.wheel(e,1))
  top=tk.Frame(body,bg=PANEL);top.pack(fill='x')
  tk.Label(top,text='COMPOSE',font=('Helvetica',10,'bold'),fg=ACCENT,bg=PANEL).pack(side='left')
  tk.Label(top,text='●  On-device AI',font=('Helvetica',10),fg=MUTED,bg=PANEL).pack(side='right')
  self.headline=tk.Label(body,text='A little room for possibility.',font=('Georgia',29),fg=FG,bg=PANEL);self.headline.pack(anchor='w',pady=(24,8))
  tk.Label(body,text='Choose your instruments. Let a new piece take shape.',font=('Helvetica',12),fg=MUTED,bg=PANEL).pack(anchor='w',pady=(0,24))
  controls=tk.Frame(body,bg=PANEL);controls.pack(fill='x')
  self.palette=tk.StringVar(value='Grand piano')
  self.combo=ttk.Combobox(controls,textvariable=self.palette,values=list(PALETTES),state='readonly',font=('Helvetica',12),width=17);self.combo.pack(side='left',fill='x',expand=True,padx=(0,14))
  self.generate=ttk.Button(controls,text='✦  Generate',style='Primary.TButton',command=self.begin);self.generate.pack(side='right')
  self.status=tk.StringVar(value='Ready to compose. Your work is saved automatically.')
  tk.Label(body,textvariable=self.status,font=('Helvetica',10),fg=MUTED,bg=PANEL,wraplength=680,justify='left').pack(anchor='w',pady=(16,8))
  self.progress=ttk.Progressbar(body,mode='indeterminate');self.progress.pack(fill='x',pady=(0,22));self.progress.pack_forget()
  self.result=tk.Frame(body,bg=BG,padx=24,pady=24);self.result.pack(fill='both',expand=True)
  tk.Label(self.result,text='YOUR COMPOSITION',font=('Helvetica',9,'bold'),fg=ACCENT,bg=BG).pack(anchor='w')
  self.title=tk.StringVar(value='Something waiting to be heard')
  tk.Label(self.result,textvariable=self.title,font=('Georgia',25),fg=FG,bg=BG,wraplength=620,justify='left').pack(anchor='w',pady=(14,9))
  self.detail=tk.StringVar(value='Fresh notes. Recorded instruments. A name of its own.')
  tk.Label(self.result,textvariable=self.detail,font=('Helvetica',11),fg=MUTED,bg=BG,wraplength=620).pack(anchor='w')
  self.roll=tk.Canvas(self.result,bg=BG,height=120,highlightthickness=0);self.roll.pack(fill='x',pady=20);self.roll.bind('<Configure>',lambda e:self.draw())
  actions=tk.Frame(self.result,bg=BG);actions.pack(fill='x');self.actions=actions
  self.exports=tk.Frame(actions,bg=BG);self.exports.pack(side='right')
  self.play=ttk.Button(actions,text='▶  Listen',style='Primary.TButton',command=self.toggle,state='disabled');self.play.pack(side='left')
  self.mid=ttk.Button(self.exports,text='Save MIDI',style='Soft.TButton',command=lambda:self.save('mid'),state='disabled');self.mid.pack(side='right',padx=(8,0))
  self.audio=ttk.Button(self.exports,text='Save M4A',style='Soft.TButton',command=lambda:self.save('m4a'),state='disabled');self.audio.pack(side='right')
  self.refresh_library();self.root.after(100,self.poll)
 def resize(self,event):
  width=max(1,event.width);self.scroll.itemconfigure(self.body_window,width=width)
  content=max(event.height,self.body.winfo_reqheight());self.scroll.itemconfigure(self.body_window,height=content)
  for frame in [self.body,self.result]:
   for widget in frame.winfo_children():
    if isinstance(widget,tk.Label):widget.configure(wraplength=max(160,width-110),justify='left')
  self.play.pack_forget();self.exports.pack_forget()
  if width<560:
   self.play.pack(side='top',fill='x');self.exports.pack(side='top',fill='x',pady=(10,0))
  else:
   self.play.pack(side='left');self.exports.pack(side='right')
  self.headline.configure(font=('Georgia',29 if width>650 else 23 if width>470 else 19))
  self.sidebar.configure(width=210 if self.root.winfo_width()>850 else 175)
  self.scroll.configure(scrollregion=self.scroll.bbox('all'))
 def wheel(self,event,direction=None):
  if not str(event.widget).startswith(str(self.body)) and event.widget!=self.scroll:return
  delta=direction if direction is not None else (-1 if event.delta>0 else 1)
  self.scroll.yview_scroll(delta,'units')
 def refresh_library(self):
  for item in self.library.get_children():self.library.delete(item)
  self.saved={}
  for path in sorted(data_dir().glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True):
   try:
    piece=json.loads(path.read_text());key=str(len(self.saved));self.saved[key]=path
    self.library.insert('', 'end', iid=key,text=piece['title'])
   except (ValueError,KeyError):continue
 def restore(self,event=None):
  if self.busy:return
  selection=self.library.selection()
  if not selection:return
  self.stop();path=self.saved[selection[0]];self.piece=json.loads(path.read_text());self.paths={k:path.with_suffix('.'+k) for k in ['mid','m4a']}
  self.title.set(self.piece['title']);self.detail.set('Saved composition · '+str(self.piece['bpm'])+' BPM')
  for button,kind in [(self.mid,'mid'),(self.audio,'m4a'),(self.play,'m4a')]:button.config(state='normal' if self.paths[kind].exists() else 'disabled')
  self.status.set('Restored your saved composition.');self.draw()
 def begin(self):
  if self.busy:return
  self.stop();self.busy=True;self.generate.config(state='disabled');self.combo.config(state='disabled')
  for button in [self.play,self.mid,self.audio]:button.config(state='disabled')
  self.status.set('Preparing the composer…');self.progress.pack(fill='x',pady=(0,16),before=self.result);self.progress.start(12)
  threading.Thread(target=self.work,args=(PALETTES[self.palette.get()],),daemon=True).start()
 def work(self,palette):
  try:
   node=executable('node')
   process=subprocess.Popen([node,str(ROOT/'desktop_engine.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT,**process_options())
   self.engine_process=process
   process.stdin.write(json.dumps({'palette':palette}));process.stdin.close()
   errors=[]
   def updates():
    for line in process.stderr:
     try:self.events.put(('status',json.loads(line)['status']))
     except (ValueError,KeyError):errors.append(line)
   reader=threading.Thread(target=updates,daemon=True);reader.start()
   output=process.stdout.read();code=process.wait();reader.join()
   if code:raise RuntimeError('Composition failed: '+''.join(errors)[-400:])
   data=json.loads(output);piece=data['piece'];folder=data_dir()
   stem=''.join(c if c.isalnum() or c in ' -' else '_' for c in piece['title'])+'-'+str(piece['seed'])
   paths={'mid':folder/(stem+'.mid'),'m4a':folder/(stem+'.m4a')}
   paths['mid'].write_bytes(base64.b64decode(data['midi']));self.events.put(('midi',(piece,paths)))
   self.events.put(('status','Selected the strongest candidate. Rendering sampled instruments…'))
   piece_path=folder/(stem+'.json');piece_path.write_text(json.dumps(piece))
   if self.closed:return
   self.render_process=subprocess.Popen(child_command('--render',piece_path,paths['m4a']),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,**process_options())
   output,error=self.render_process.communicate()
   if self.render_process.returncode:raise RuntimeError(error[-400:])
   self.events.put(('ready',json.loads(output)))
  except Exception as e:self.events.put(('error',str(e)))
 def poll(self):
  try:
   while True:
    kind,value=self.events.get_nowait()
    if kind=='status':self.status.set(value)
    elif kind=='midi':
     self.piece,self.paths=value;self.title.set(self.piece['title']);seconds=round(self.piece['seconds'])
     self.detail.set(' + '.join(dict.fromkeys(self.piece['instrument_names']))+f" · {self.piece['bpm']} BPM · {seconds//60}:{seconds%60:02d}")
     self.mid.config(state='normal');self.draw()
    elif kind=='ready':
     self.play.config(state='normal');self.audio.config(state='normal');self.status.set('Ready to listen. Saved to your library.');self.refresh_library();self.finish()
    elif kind=='error':self.status.set(value);self.finish()
  except queue.Empty:pass
  if self.player and self.player.poll() is not None:self.player=None;self.play.config(text='▶ Listen')
  self.root.after(100,self.poll)
 def finish(self):
  self.progress.stop();self.progress.pack_forget();self.busy=False;self.generate.config(state='normal');self.combo.config(state='readonly')
 def draw(self):
  self.roll.delete('all')
  if not self.piece:return
  width=max(1,self.roll.winfo_width());height=max(1,self.roll.winfo_height());end=self.piece['bars']*4
  for bar in range(self.piece['bars']):
   x=bar*4/end*width;self.roll.create_line(x,0,x,height,fill='#1c2d34')
  for n in self.piece['notes']:
   x=n['beat']/end*width;y=height-12-(n['pitch']-30)/70*(height-24)
   self.roll.create_rectangle(x,y,x+max(2,n['duration']/end*width),y+2,fill=ACCENT if n['voice']==0 else '#82956a',outline='')
 def toggle(self):
  if self.player:self.stop();return
  self.player=subprocess.Popen(child_command('--play',self.paths['m4a']),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**process_options())
  self.play.config(text='■ Stop')
 def stop(self):
  if self.player and self.player.poll() is None:self.player.terminate()
  self.player=None;self.play.config(text='▶ Listen')
 def save(self,kind):
  target=filedialog.asksaveasfilename(initialfile=self.paths[kind].name,defaultextension='.'+kind,filetypes=[(kind.upper(),'*.'+kind)])
  if target and Path(target).resolve()!=self.paths[kind].resolve():shutil.copyfile(self.paths[kind],target)
 def about(self):
  report=json.loads((ROOT/'dist/training-report.json').read_text());specialists=list((ROOT/'dist/instruments').glob('*/model.json'))
  messagebox.showinfo('About Cadenza',f"Native Python UI. Local neural inference via Node.js.\n\nMusic model: {report['parameters']:,} parameters; {report['statistics']['train_performances']:,} training MIDI performances/parts.\nInstrument specialists: {len(specialists)}.\n\nAn experimental short-context model with generated form and heuristic selection. More data and lower loss do not prove better music.\n\nGeneralUser GS sound bank: S. Christian Collins. MAESTRO-derived models: noncommercial CC BY-NC-SA 4.0. Sources and reports included.")
 def close(self):
  self.closed=True;self.stop()
  for process in [self.engine_process,self.render_process]:
   if process and process.poll() is None:process.terminate()
  self.root.destroy()
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--render':
  from render_portable import render
  print(json.dumps(render(json.loads(Path(sys.argv[2]).read_text()),Path(sys.argv[3]))))
 elif len(sys.argv)>1 and sys.argv[1]=='--play':
  from playback import play
  play(Path(sys.argv[2]))
 elif len(sys.argv)>1 and sys.argv[1]=='--smoke':
  from packaged_smoke import check
  check()
 else:Cadenza().root.mainloop()
