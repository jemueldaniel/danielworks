"""Loopback-only backend. Demo profiles are policy fixtures, NOT authentication."""
from __future__ import annotations
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit
import uuid

from workbench import Store, InvalidInput, CheckpointError

PROFILES = {'reader': ('demo', False), 'operator': ('demo', True), 'other-reader': ('other', False)}


def decode_json(raw: bytes):
    def pairs(values):
        out = {}
        for key, value in values:
            if key in out:
                raise ValueError()
            out[key] = value
        return out
    def constant(_):
        raise ValueError()
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise InvalidInput('invalid_json') from None


class BoundedServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def __init__(self, address, handler):
        self.slots = threading.BoundedSemaphore(12)
        super().__init__(address, handler)
    def process_request(self, request, client_address):
        request.settimeout(5)
        if not self.slots.acquire(blocking=False):
            try:
                body=b'{"error":"server_busy"}'
                request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body)
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request,client_address)
        except BaseException:
            self.slots.release()
            raise
    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request,client_address)
        finally:
            self.slots.release()


def create_server(path: str | Path, port: int = 0, *, diagnostics: bool = False):
    store=Store(path)
    class Handler(BaseHTTPRequestHandler):
        server_version='Workbench/0.1'
        sys_version=''
        def log_message(self,*args):
            pass  # never echo URL, headers or submitted content
        def _reply(self,status,value):
            data=json.dumps(value,allow_nan=False,separators=(',',':')).encode('utf-8')
            if len(data)>65_536:
                status,data=500,b'{"error":"response_limit"}'
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Request-Id',self.request_id)
            self.send_header('Connection','close')
            self.end_headers()
            self.close_connection=True
            try:
                self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):
                pass  # committed work remains inspectable after lost response
            if diagnostics:
                print(json.dumps({'event':'http','request_id':self.request_id,'status':status,
                                  'method':self.command if self.command in ('GET','POST') else 'other',
                                  'elapsed_ms':round((time.monotonic()-self.started)*1000)}),file=sys.stderr,flush=True)
        def _body(self):
            if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
                return None,415
            values=self.headers.get_all('Content-Length',[])
            if len(values)!=1 or not re.fullmatch(r'[0-9]{1,9}',values[0]) or self.headers.get('Transfer-Encoding'):
                return None,400
            size=int(values[0])
            if size>8192:
                return None,413
            raw=self.rfile.read(size)
            if len(raw)!=size:
                raise InvalidInput('incomplete_body')
            return decode_json(raw),None
        def _handle(self):
            self.request_id=str(uuid.uuid4()); self.started=time.monotonic()
            expected=f'127.0.0.1:{self.server.server_address[1]}'
            if self.headers.get_all('Host',[]) != [expected]:
                return self._reply(403,{'error':'host_denied'})
            origins=self.headers.get_all('Origin',[])
            if origins and origins!=['http://'+expected]:
                return self._reply(403,{'error':'origin_denied'})
            profile=self.headers.get('X-Workbench-Profile','reader')
            if profile not in PROFILES or len(self.headers.get_all('X-Workbench-Profile',[]))>1:
                return self._reply(403,{'error':'permission_denied'})
            tenant,write=PROFILES[profile]
            if self.command not in ('GET','POST'):
                return self._reply(405,{'error':'method_not_allowed'})
            if self.command=='POST' and not write:
                return self._reply(403,{'error':'permission_denied'})
            parsed=urlsplit(self.path)
            if parsed.scheme or parsed.netloc or parsed.fragment or len(self.path)>1024:
                raise InvalidInput()
            query=parse_qs(parsed.query,keep_blank_values=True)
            if any(len(value)!=1 for value in query.values()):
                raise InvalidInput()
            path=parsed.path
            if self.command=='GET':
                if path=='/health' and not query:
                    return self._reply(200,{'status':'ok','database':'sqlite','schema_version':1})
                if path=='/v1/dataset' and not query:
                    return self._reply(200,store.description())
                if path=='/v1/search' and set(query)<= {'q','k'}:
                    return self._reply(200,{'items':store.search(query.get('q',[''])[0],int(query.get('k',['2'])[0]))})
                if path=='/v1/jobs' and set(query)<= {'limit','cursor'}:
                    return self._reply(200,store.list(tenant,limit=int(query.get('limit',['10'])[0]),cursor=query.get('cursor',[None])[0]))
                match=re.fullmatch(r'/v1/jobs/([a-z][a-z0-9_-]{0,63})',path)
                if match and not query:
                    found=store.inspect(tenant,match[1])
                    return self._reply(200,found) if found else self._reply(404,{'error':'not_found'})
            else:
                if query:
                    raise InvalidInput()
                body,status=self._body()
                if status:
                    return self._reply(status,{'error':{400:'invalid_length',413:'body_too_large',415:'media_type'}[status]})
                if path=='/v1/jobs':
                    return self._reply(200,store.submit(tenant,body))
                if path=='/v1/work':
                    if type(body) is not dict or not set(body)<= {'max_cases'}:
                        raise InvalidInput()
                    return self._reply(200,store.work(tenant,max_cases=body.get('max_cases',5)))
                match=re.fullmatch(r'/v1/jobs/([a-z][a-z0-9_-]{0,63})/cancel',path)
                if match:
                    if body!={}:
                        raise InvalidInput()
                    return self._reply(200,{'cancelled':store.cancel(tenant,match[1])})
            self._reply(404,{'error':'not_found'})
        def _safe(self):
            try:
                self._handle()
            except InvalidInput as error:
                self._reply(409 if error.code=='idempotency_conflict' else 400,{'error':error.code})
            except CheckpointError:
                self._reply(409,{'error':'integrity_error'})
            except (ValueError,TypeError,OverflowError):
                self._reply(400,{'error':'invalid_input'})
            except sqlite3.OperationalError:
                self._reply(503,{'error':'database_unavailable'})
            except (ConnectionResetError,BrokenPipeError,TimeoutError):
                self.close_connection=True
            except Exception:
                self._reply(500,{'error':'internal_error'})
        do_GET=_safe
        do_POST=_safe
        do_PUT=_safe
        do_DELETE=_safe
        do_OPTIONS=_safe
    return BoundedServer(('127.0.0.1',port),Handler)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['serve','work'])
    parser.add_argument('--db',type=Path,required=True,help='Explicit, isolated workbench SQLite file; never a production DB')
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--max-cases',type=int,default=5)
    parser.add_argument('--lease-ms',type=int,default=30000)
    args=parser.parse_args()
    args.db.parent.mkdir(parents=True,exist_ok=True)
    if args.mode=='work':
        result=Store(args.db).work('demo',max_cases=args.max_cases,lease_ms=args.lease_ms,
                                  observer=lambda event:print(json.dumps(event),flush=True))
        print(json.dumps(result,sort_keys=True),flush=True)
        return
    server=create_server(args.db,args.port,diagnostics=True)
    print(json.dumps({'event':'ready','port':server.server_address[1],'database':'sqlite'}),flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__=='__main__':
    main()
