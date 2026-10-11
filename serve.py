"""Local-only app server with macOS sampled instruments and M4A rendering."""
import argparse
import json
import math
import tempfile
import threading
import webbrowser
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from render_piano import render

ROOT=Path(__file__).resolve().parent
RENDER_LOCK=threading.Lock()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'dist'),**kwargs)
    def do_GET(self):
        if self.path=='/api/capabilities':
            data=b'{"sampled_instruments":true,"m4a":true,"local":true}'
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        else:super().do_GET()
    def do_POST(self):
        if self.path!='/api/render':self.send_error(404);return
        expected='http://'+self.headers.get('Host','')
        if self.headers.get('Origin',expected)!=expected:self.send_error(403);return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=1000000:raise ValueError('Invalid composition size')
            piece=json.loads(self.rfile.read(length))
            if not 40<=piece['bpm']<=180 or not 0<piece['seconds']<=240:raise ValueError('Invalid duration or tempo')
            if not 1<=piece['bars']<=64 or not 1<=len(piece['notes'])<=5000:raise ValueError('Invalid composition')
            programs=piece.get('programs',[0,0])
            if len(programs)!=2 or any(type(p) is not int or not 0<=p<=127 for p in programs):raise ValueError('Invalid instrument')
            for n in piece['notes']:
                if n['voice'] not in [0,1] or type(n['pitch']) is not int or not 0<=n['pitch']<=127:raise ValueError('Invalid note')
                if not 1<=n['velocity']<=127 or not math.isfinite(n['beat']) or not 0<=n['beat']<=256 or not math.isfinite(n['duration']) or not 0<n['duration']<=8:raise ValueError('Invalid note timing')
            with RENDER_LOCK,tempfile.TemporaryDirectory(prefix='cadenza-export-') as tmp:
                path=Path(tmp)/'composition.m4a';render(piece,path);audio=path.read_bytes()
                archive=ROOT/'generated';archive.mkdir(exist_ok=True)
                stem=''.join(c if c.isalnum() or c in ' -' else '_' for c in piece['title'])+'-'+str(piece['seed'])
                (archive/(stem+'.json')).write_text(json.dumps(piece))
                (archive/(stem+'.m4a')).write_bytes(audio)
            self.send_response(200);self.send_header('Content-Type','audio/mp4');self.send_header('Content-Length',str(len(audio)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(audio)
        except Exception as e:
            data=json.dumps({'error':str(e)}).encode();self.send_response(400);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8765);ap.add_argument('--open',action='store_true');a=ap.parse_args()
    try:server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
    except OSError:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{a.port}/api/capabilities',timeout=2) as r:
                existing=json.load(r)
            if existing.get('sampled_instruments') and existing.get('local'):
                print(f'Cadenza is already running at http://127.0.0.1:{a.port}',flush=True)
                if a.open:webbrowser.open(f'http://127.0.0.1:{a.port}')
                return
        except Exception:pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    url=f'http://127.0.0.1:{server.server_port}'
    print(f'Cadenza runs locally at {url}',flush=True)
    if a.open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
