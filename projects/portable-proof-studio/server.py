"""Loopback-only demo HTTP app; deliberately not a production web gateway."""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from store import DemoError, ProofStore

STATIC = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
    '/style.css': ('style.css', 'text/css; charset=utf-8'),
}


def _strict_pairs(items):
    out={}
    for k,v in items:
        if k in out: raise DemoError('DUPLICATE_JSON_KEY')
        out[k]=v
    return out


def make_handler(store: ProofStore):
    web = Path(__file__).parent / 'web'

    class Handler(BaseHTTPRequestHandler):
        server_version = 'PortableProof/0.1'
        sys_version = ''

        def log_message(self, *_args):
            # Keep bearer workspace tokens and user input out of console logs.
            pass

        def _send(self, status: int, result, content_type='application/json; charset=utf-8'):
            if not isinstance(result, bytes):
                body=json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
            else:body=result
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',
                             "default-src 'none'; script-src 'self'; style-src 'self'; "
                             "connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            try:self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError):pass

        def _origin_ok(self):
            host=self.headers.get('Host','')
            port=self.server.server_address[1]
            allowed={f'127.0.0.1:{port}', f'localhost:{port}'}
            if host not in allowed:raise DemoError('HOST_DENIED',403)
            origin=self.headers.get('Origin')
            if origin is not None and origin not in {'http://'+x for x in allowed}:
                raise DemoError('ORIGIN_DENIED',403)

        def _token(self):
            return self.headers.get('X-Demo-Workspace','')

        def _key(self):
            return self.headers.get('Idempotency-Key','')

        def _body(self):
            if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
                raise DemoError('JSON_REQUIRED',415)
            raw=self.headers.get('Content-Length','')
            if not raw.isdecimal():raise DemoError('BODY_LENGTH_REQUIRED',411)
            size=int(raw)
            if size<=0 or size>8192:raise DemoError('BODY_SIZE_INVALID',413)
            self._body_started = True
            data=self.rfile.read(size)
            if len(data)!=size:raise DemoError('BODY_INCOMPLETE')
            try:payload=json.loads(data.decode('utf-8','strict'),object_pairs_hook=_strict_pairs,
                                  parse_constant=lambda _:(_ for _ in ()).throw(DemoError('INVALID_NUMBER')))
            except (UnicodeError,json.JSONDecodeError):raise DemoError('INVALID_JSON')
            if not isinstance(payload,dict):raise DemoError('JSON_OBJECT_REQUIRED')
            return payload

        def _drain_early_request(self):
            # Windows may abort a just-sent HTTP error if unread POST bytes
            # remain buffered when the connection closes. Only consume a
            # single, valid and small declared length, never transfer codings
            # or ambiguous/oversized input.
            if self.headers.get_all('Transfer-Encoding'):
                return
            lengths = self.headers.get_all('Content-Length', [])
            if len(lengths) != 1:
                return
            raw = lengths[0]
            if not raw.isascii() or not raw.isdecimal() or len(raw)>5:
                return
            size = int(raw)
            if size>8192:
                return
            self.connection.settimeout(0.5)
            try:
                while size:
                    part = self.rfile.read(min(size, 4096))
                    if not part: break
                    size -= len(part)
            except (OSError,TimeoutError):
                pass

        def _process(self, method):
            self._body_started = False
            try:
                self._origin_ok()
                path=urlsplit(self.path)
                if path.query or path.fragment:raise DemoError('UNEXPECTED_QUERY')
                if method=='GET' and path.path in STATIC:
                    fname,mime=STATIC[path.path]
                    self._send(200,(web/fname).read_bytes(),mime)
                    return
                if method=='GET' and path.path=='/api/health':
                    self._send(200,{'status':'ok','scope':'loopback-only demo; not public authentication'})
                    return
                if method=='POST' and path.path=='/api/workspaces':
                    obj=self._body()
                    if obj:raise DemoError('INVALID_FIELDS')
                    self._send(201,store.create_workspace());return
                token=self._token()
                if method=='GET':
                    if path.path=='/api/workflows':v=store.list_workflows(token)
                    elif path.path=='/api/documents':v=store.list_documents(token)
                    elif path.path=='/api/evaluations':v=store.list_evaluations(token)
                    elif path.path.startswith('/api/runs/'):
                        v=store.get_run(token,path.path.removeprefix('/api/runs/'))
                    else:raise DemoError('NOT_FOUND',404)
                    self._send(200,{'data':v});return
                if method=='POST':
                    payload=self._body();key=self._key()
                    if path.path=='/api/workflows':v=store.create_workflow(token,key,payload)
                    elif path.path=='/api/workflows/update':v=store.update_workflow(token,key,payload)
                    elif path.path=='/api/runs':v=store.run_workflow(token,key,payload)
                    elif path.path=='/api/documents':v=store.create_document(token,key,payload)
                    elif path.path=='/api/documents/update':v=store.update_document(token,key,payload)
                    elif path.path=='/api/documents/delete':v=store.delete_document(token,key,payload)
                    elif path.path=='/api/search':v=store.search(token,payload)
                    elif path.path=='/api/evaluations':v=store.evaluate(token,key,payload)
                    else:raise DemoError('NOT_FOUND',404)
                    self._send(200,{'data':v});return
                raise DemoError('METHOD_NOT_ALLOWED',405)
            except DemoError as e:
                if method == 'POST' and not self._body_started:
                    self._drain_early_request()
                self._send(e.status,{'error':{'code':e.code}})
            except (OSError,ValueError,TypeError,OverflowError):
                self._send(500,{'error':{'code':'SERVICE_ERROR'}})

        def do_GET(self):self._process('GET')
        def do_POST(self):self._process('POST')
        def do_PUT(self):self._process('PUT')
        def do_DELETE(self):self._process('DELETE')
    return Handler


def start(db_path: str | Path, port: int = 0) -> ThreadingHTTPServer:
    if not isinstance(port,int) or not 0<=port<=65535:raise ValueError('invalid port')
    store=ProofStore(db_path)
    server=ThreadingHTTPServer(('127.0.0.1',port),make_handler(store))
    server.daemon_threads=True
    return server


def main():
    parser=argparse.ArgumentParser(description='Local, synthetic Workflow → Knowledge reference demo')
    parser.add_argument('--db',type=Path,default=Path('./portable-proof.sqlite'))
    parser.add_argument('--port',type=int,default=8078)
    args=parser.parse_args()
    srv=start(args.db,args.port)
    print(f'Open http://127.0.0.1:{srv.server_address[1]}/ (local demonstration only)',flush=True)
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()

if __name__=='__main__':main()
