"""Tests actual HTTP transport, SQLite persistence and loopback source serving."""
from __future__ import annotations
import http.client
import json
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from server import start


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.db=Path(self.t.name)/'db.sqlite'
        self._boot()

    def _boot(self):
        self.srv=start(self.db,0)
        self.port=self.srv.server_address[1]
        self.th=threading.Thread(target=self.srv.serve_forever,daemon=True)
        self.th.start()

    def _stop(self):
        self.srv.shutdown();self.th.join(5);self.srv.server_close()

    def tearDown(self):self._stop()

    def call(self, method, path, obj=None, token=None, key=None, headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        h={'Host':f'127.0.0.1:{self.port}','Accept':'application/json'}
        if obj is not None:h['Content-Type']='application/json'
        if token:h['X-Demo-Workspace']=token
        if key:h['Idempotency-Key']=key
        if headers:h.update(headers)
        data=None if obj is None else json.dumps(obj).encode('utf8')
        conn.request(method,path,data,headers=h)
        r=conn.getresponse();body=r.read();head={k.lower():v for k,v in r.getheaders()};code=r.status
        conn.close()
        try:v=json.loads(body)
        except ValueError:v=body
        return code,v,head

    def space(self):
        code,v,_=self.call('POST','/api/workspaces',{})
        self.assertEqual(code,201)
        return v['workspaceToken']

    def test_static_assets_and_security_headers(self):
        for path in ['/','/app.js','/style.css']:
            code,body,head=self.call('GET',path)
            self.assertEqual(code,200)
            self.assertTrue(body)
            self.assertEqual(head.get('x-content-type-options'),'nosniff')
            self.assertEqual(head.get('cache-control'),'no-store')
            self.assertIn('script-src',head.get('content-security-policy',''))

    def test_host_and_origin_refuse_cross_site_requests(self):
        code,j,_=self.call('GET','/api/health',headers={'Host':'host.invalid'})
        self.assertEqual((code,j['error']['code']),(403,'HOST_DENIED'))
        code,j,_=self.call('POST','/api/workspaces',{},headers={'Origin':'https://attacker.example'})
        self.assertEqual((code,j['error']['code']),(403,'ORIGIN_DENIED'))

    def test_rejects_invalid_json_and_media_types(self):
        t=self.space()
        code,j,_=self.call('POST','/api/workflows',{'title':'A'},t,'test-run-123',{'Content-Type':'text/plain'})
        self.assertEqual((code,j['error']['code']),(415,'JSON_REQUIRED'))
        # Raw socket request to trigger duplicate JSON keys.
        c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        c.request('POST','/api/workflows',b'{"title":"A","title":"B"}',headers={
            'Content-Type':'application/json','X-Demo-Workspace':t,'Idempotency-Key':'test-run-456'})
        v=c.getresponse();self.assertEqual(v.status,400)
        self.assertEqual(json.loads(v.read())['error']['code'],'DUPLICATE_JSON_KEY');c.close()

    def test_unexpected_routes_queries_and_methods_fail_safely(self):
        for method,path in [('GET','/../store.py'),('GET','/api/health?x=1'),('PUT','/api/workspaces'),('GET','/does-not-exist')]:
            c,v,_=self.call(method,path)
            self.assertGreaterEqual(c,400)
            self.assertIn('error',v)

    def test_repeated_early_post_rejections_deliver_http_response(self):
        for _ in range(16):
            code, body, _ = self.call('POST','/api/workspaces',{},
                                      headers={'Origin':'https://attacker.example'})
            self.assertEqual((code,body['error']['code']),(403,'ORIGIN_DENIED'))
        token=self.space()
        for _ in range(16):
            code, body, _ = self.call('POST','/api/workflows',{'title':'A'},
                                      token, 'new-key-abc',
                                      headers={'Content-Type':'text/plain'})
            self.assertEqual((code,body['error']['code']),(415,'JSON_REQUIRED'))
        self.assertEqual(self.call('GET','/api/workflows',token=token)[1]['data'],[])

    def test_wrong_post_route_with_body_remains_side_effect_free(self):
        token=self.space()
        for _ in range(12):
            code, body, _ = self.call('POST','/api/no-such-path',{'text':'abc'},
                                      token,'new-key-abc')
            self.assertEqual((code,body['error']['code']),(404,'NOT_FOUND'))
        self.assertEqual(self.call('GET','/api/workflows',token=token)[1]['data'],[])

    def test_requires_token_and_mutation_key(self):
        code,v,_=self.call('GET','/api/documents')
        self.assertEqual((code,v['error']['code']),(401,'SESSION_REQUIRED'))
        t=self.space()
        code,v,_=self.call('POST','/api/workflows',{'title':'A'},t)
        self.assertEqual(v['error']['code'],'INVALID_OPERATION_KEY')

    def test_http_full_workflow_to_knowledge_persists_restart(self):
        t=self.space()
        code,create,_=self.call('POST','/api/workflows',{'title':'A','maxKeywords':4},t,'workflow-key-1')
        self.assertEqual(code,200)
        wid=create['data']['workflowId']
        runbody={'workflowId':wid,'text':'evidence system evidence token'}
        _,run,_=self.call('POST','/api/runs',runbody,t,'run-idem-key-1')
        run=run['data'];self.assertEqual(run['artifactText'],'evidence\nsystem\ntoken')
        _,again,_=self.call('POST','/api/runs',runbody,t,'run-idem-key-1')
        self.assertEqual(again['data']['runId'],run['runId'])
        _,d,_=self.call('POST','/api/documents',{'title':'Imported','sourceRunId':run['runId']},t,'document-key-1')
        docid=d['data']['documentId']
        _,search,_=self.call('POST','/api/search',{'query':'evidence'},t)
        self.assertEqual(search['data']['results'][0]['documentId'],docid)
        self._stop()
        self._boot()
        _,doclist,_=self.call('GET','/api/documents',token=t)
        self.assertEqual(doclist['data'][0]['id'],docid)
        _,replay,_=self.call('POST','/api/runs',runbody,t,'run-idem-key-1')
        self.assertEqual(replay['data']['runId'],run['runId'])
        _,evaluation,_=self.call('POST','/api/evaluations',
            {'query':'evidence','expectedDocumentId':docid},t,'evaluation-key-1')
        self.assertTrue(evaluation['data']['passed'])
        self.assertEqual(len(self.call('GET','/api/evaluations',token=t)[1]['data']),1)

    def test_two_http_sessions_are_isolated(self):
        t1,t2=self.space(),self.space()
        _,d,_=self.call('POST','/api/documents',{'title':'A','text':'private fixture sample'},t1,'doc-idempotent-1')
        self.assertEqual(self.call('POST','/api/search',{'query':'sample'},t2)[1]['data']['results'],[])
        code,j,_=self.call('POST','/api/evaluations',
                           {'query':'sample','expectedDocumentId':d['data']['documentId']},t2,'eval-not-own-1')
        self.assertEqual((code,j['error']['code']),(404,'EXPECTED_DOCUMENT_NOT_FOUND'))

    def test_unchanged_operation_key_changed_payload_conflicts(self):
        t=self.space()
        self.call('POST','/api/workflows',{'title':'A'},t,'stable-key-01')
        code,j,_=self.call('POST','/api/workflows',{'title':'B'},t,'stable-key-01')
        self.assertEqual((code,j['error']['code']),(409,'OPERATION_CONFLICT'))


if __name__=='__main__':unittest.main()
