"""Local static server and fixed-origin API proxy; no third-party dependencies."""
import os, json, urllib.request, urllib.error
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]/'dist'
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
 def do_GET(self):
  if self.path.startswith(('/api/','/products')):self.proxy()
  else:super().do_GET()
 def do_POST(self):self.proxy()
 def proxy(self):
  if self.path.startswith(('/api/v0/auth/','/api/v0/users/')):origin=os.getenv('USER_SERVICE_URL','http://127.0.0.1:8082')
  elif self.path.startswith('/api/v0/applications'):origin=os.getenv('APPLICATION_SERVICE_URL','http://127.0.0.1:8083')
  elif self.path=='/products' or self.path.startswith('/products/'):origin=os.getenv('PRODUCT_SERVICE_URL','http://127.0.0.1:8081')
  else:self.send_error(404);return
  size=int(self.headers.get('Content-Length',0))
  if size>1000000:self.send_error(413);return
  headers={k:self.headers[k] for k in ['Authorization','Content-Type'] if k in self.headers}
  req=urllib.request.Request(origin+self.path,data=self.rfile.read(size) if size else None,headers=headers,method=self.command)
  try:
   with urllib.request.urlopen(req,timeout=18) as r:status=r.status;body=r.read();content=r.headers.get('Content-Type','application/json')
  except urllib.error.HTTPError as e:status=e.code;body=e.read();content='application/json'
  except (OSError,urllib.error.URLError):status=502;body=json.dumps({'message':'Backend недоступен. Запустите сервисы 8081, 8082, 8083.'},ensure_ascii=False).encode();content='application/json; charset=utf-8'
  self.send_response(status);self.send_header('Content-Type',content);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
if __name__=='__main__':
 port=int(os.getenv('PORT','8085'));print(f'Frontend: http://localhost:{port}',flush=True);ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
