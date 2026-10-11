"""Actual loopback sockets and disk SQLite, not HTTP mocks."""
import concurrent.futures
from email.message import Message
import io
import time
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from server import create_server

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.server=create_server(Path(self.tmp.name)/'http.sqlite3',0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start(); self.port=self.server.server_address[1]
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(3); self.tmp.cleanup()
    def request(self, method, path, body=None, headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=4)
        raw=json.dumps(body).encode() if isinstance(body,dict) else body
        h={'X-Workbench-Profile':'operator','Content-Type':'application/json'}; h.update(headers or {})
        try:
            connection.request(method,path,body=raw,headers=h)
            response=connection.getresponse(); data=response.read()
            return response.status, json.loads(data), dict(response.getheaders())
        finally: connection.close()
    def fake_rejection(self, status, payload, headers, *, body_read=False):
        """Exercise response-body accounting without opening a diagnostic socket."""
        handler=self.server.RequestHandlerClass.__new__(self.server.RequestHandlerClass)
        handler.command='POST'
        handler.request_id='test-request'
        handler.started=time.monotonic()
        handler.headers=Message()
        for key,value in headers:
            handler.headers.add_header(key,value)
        handler.rfile=io.BytesIO(payload)
        handler.wfile=io.BytesIO()
        handler.close_connection=False
        handler._post_body_read=body_read
        handler.status_written=None
        handler.send_response=lambda value: setattr(handler,'status_written',value)
        handler.send_header=lambda *args: None
        handler.end_headers=lambda: None
        handler._reply(status,{'error':'rejected'})
        return handler

    def test_rejected_bounded_post_payload_is_accounted_before_connection_close(self):
        for status,count in ((403,2),(415,2),(413,8193)):
            with self.subTest(status=status,count=count):
                handler=self.fake_rejection(status,b'x'*count+b'next',
                                            [('Content-Length',str(count))])
                self.assertEqual(handler.status_written,status)
                self.assertEqual(handler.rfile.read(),b'next')
                self.assertTrue(handler._post_body_read)
                self.assertTrue(handler.close_connection)

    def test_rejected_payload_accounting_is_strictly_bounded_and_never_double_reads(self):
        for headers in (
            [('Content-Length','8194')],
            [('Content-Length','2'),('Content-Length','2')],
            [('Content-Length','2'),('Transfer-Encoding','chunked')],
            [('Content-Length','9999999999999999999999')],
        ):
            with self.subTest(headers=headers):
                handler=self.fake_rejection(413,b'xxnext',headers)
                self.assertEqual(handler.rfile.tell(),0)
        already=self.fake_rejection(400,b'next',[('Content-Length','4')],body_read=True)
        self.assertEqual(already.rfile.read(),b'next')
        success=self.fake_rejection(200,b'next',[('Content-Length','4')])
        self.assertEqual(success.rfile.read(),b'next')

    def test_health_crosses_a_real_socket(self):
        status,data,headers=self.request('GET','/health')
        self.assertEqual(status,200); self.assertEqual(data['database'],'sqlite')
        self.assertEqual(headers['Cache-Control'],'no-store')
    def test_end_to_end_http_persistence_and_grading(self):
        status,created,_=self.request('POST','/v1/jobs',{'key':'http-run','engine':'fts5','k':2})
        self.assertEqual(status,200)
        status,work,_=self.request('POST','/v1/work',{})
        self.assertEqual(status,200); self.assertEqual(work['job']['state'],'done')
        status,restored,_=self.request('GET','/v1/jobs/http-run')
        self.assertEqual(restored['result']['mrr_at_k'],0.8)
    def test_read_profile_cannot_mutate(self):
        status,body,_=self.request('POST','/v1/jobs',{'key':'blocked','engine':'fts5','k':2},{'X-Workbench-Profile':'reader'})
        self.assertEqual(status,403); self.assertEqual(body['error'],'permission_denied')
        self.assertEqual(self.request('GET','/v1/jobs')[1]['items'],[])
    def test_duplicate_write_conflict_and_race(self):
        body={'key':'shared','engine':'fts5','k':2}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            statuses=list(pool.map(lambda _:self.request('POST','/v1/jobs',body)[0],range(6)))
        self.assertEqual(statuses,[200]*6)
        self.assertEqual(len(self.request('GET','/v1/jobs')[1]['items']),1)
        self.assertEqual(self.request('POST','/v1/jobs',{**body,'k':3})[0],409)
    def test_bad_json_and_duplicate_keys_are_rejected(self):
        for body in (b'{',b'{"key":"one","key":"two","engine":"fts5","k":2}',b'{"key":"one","engine":"fts5","k":NaN}'):
            self.assertEqual(self.request('POST','/v1/jobs',body)[0],400)
        self.assertEqual(self.request('GET','/v1/jobs')[1]['items'],[])
    def test_content_type_size_origin_and_host(self):
        self.assertEqual(self.request('POST','/v1/jobs',b'{}',{'Content-Type':'text/plain'})[0],415)
        self.assertEqual(self.request('POST','/v1/jobs',b'x'*8193)[0],413)
        self.assertEqual(self.request('POST','/v1/jobs',b'{}',{'Origin':'https://untrusted.example'})[0],403)
        self.assertEqual(self.request('GET','/health',headers={'Host':'untrusted.example'})[0],403)
    def test_partition_unknown_profile_and_pagination_bounds(self):
        self.request('POST','/v1/jobs',{'key':'private-to-demo','engine':'fts5','k':2})
        self.assertEqual(self.request('GET','/v1/jobs',headers={'X-Workbench-Profile':'other-reader'})[1]['items'],[])
        self.assertEqual(self.request('GET','/v1/jobs',headers={'X-Workbench-Profile':'admin'})[0],403)
        self.assertEqual(self.request('GET','/v1/jobs?limit=21')[0],400)
        self.assertEqual(self.request('GET','/v1/jobs?limit=2&limit=3')[0],400)
    def test_real_search_and_cancel_are_exposed(self):
        self.assertEqual(self.request('GET','/v1/search?q=password&k=2')[1]['items'][0]['id'],'alpha')
        self.request('POST','/v1/jobs',{'key':'cancelled','engine':'fts5','k':2})
        self.assertTrue(self.request('POST','/v1/jobs/cancelled/cancel',{})[1]['cancelled'])
        self.assertIsNone(self.request('POST','/v1/work',{})[1]['job'])

if __name__=='__main__': unittest.main()
