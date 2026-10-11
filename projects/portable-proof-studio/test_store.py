"""Real SQLite state, idempotency, isolation and restart acceptance tests."""
from __future__ import annotations
import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from store import DemoError, ProofStore


@contextmanager
def managed_test_connection(path: Path):
    """sqlite3.Connection.__exit__ commits, but does NOT close Windows handles."""
    connection = sqlite3.connect(path)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'demo.sqlite'
        self.s = ProofStore(self.path)
        self.a = self.s.create_workspace()['workspaceToken']
        self.b = self.s.create_workspace()['workspaceToken']

    def create(self, token=None, key='workflowkey1'):
        return self.s.create_workflow(token or self.a, key, {'title':'Evidence', 'maxKeywords':5, 'minLength':2})

    def sample_run(self, workflow=None, token=None, key='run-abc123'):
        if workflow is None: workflow=self.create()
        return self.s.run_workflow(token or self.a,key,{
            'workflowId':workflow['workflowId'], 'text':'HELLO  world, hello evidence verified'})

    def assert_code(self, code, fn):
        with self.assertRaises(DemoError) as ctx: fn()
        self.assertEqual(ctx.exception.code,code)

    def test_workspace_token_is_not_stored_in_plaintext(self):
        with managed_test_connection(self.path) as db:
            cells=db.execute('SELECT token_hash FROM workspaces').fetchall()
        self.assertNotIn(self.a,str(cells));self.assertEqual(len(cells),2)

    def test_explicit_sqlite_fixture_close_allows_immediate_cleanup(self):
        path = Path(self.temp.name) / 'temporary-test-handle.sqlite'
        with managed_test_connection(path) as db:
            db.execute('CREATE TABLE evidence(id INTEGER)')
            db.execute('INSERT INTO evidence VALUES (1)')
        path.unlink()
        self.assertFalse(path.exists())

    def test_workspace_reloads_from_real_database(self):
        w=self.create()
        self.assertEqual(self.s.list_workflows(self.a)[0]['id'],w['workflowId'])
        restarted=ProofStore(self.path)
        self.assertEqual(restarted.list_workflows(self.a)[0]['id'],w['workflowId'])

    def test_no_unauthenticated_or_foreign_list(self):
        self.create()
        self.assert_code('SESSION_REQUIRED',lambda:self.s.list_workflows(''))
        self.assertEqual(self.s.list_workflows(self.b),[])

    def test_expired_token_denies_before_replay(self):
        self.create()
        with managed_test_connection(self.path) as db:db.execute('UPDATE workspaces SET expires=0')
        self.assert_code('SESSION_REQUIRED',lambda:self.create())
        self.assert_code('SESSION_REQUIRED',lambda:self.s.list_workflows(self.a))

    def test_four_actual_steps_and_saved_artifact(self):
        r=self.sample_run()
        self.assertEqual(r['status'],'succeeded')
        self.assertEqual(len(r['trace']),4)
        self.assertEqual(r['artifactText'],'hello\nworld\nevidence\nverified')
        self.assertEqual(self.s.get_run(self.a,r['runId'])['artifactText'],r['artifactText'])

    def test_exact_replay_returns_same_run_and_single_artifact(self):
        w=self.create();r=self.sample_run(w)
        again=self.sample_run(w)
        self.assertEqual(r,again)
        with managed_test_connection(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM runs').fetchone()[0],1)

    def test_changed_intent_under_same_key_conflicts(self):
        w=self.create()
        self.sample_run(w)
        self.assert_code('OPERATION_CONFLICT',lambda:self.s.run_workflow(self.a,'run-abc123',
            {'workflowId':w['workflowId'],'text':'changed'}))

    def test_operation_replay_is_isolated_by_workspace(self):
        a=self.create(self.a,key='same-operation-1')
        b=self.create(self.b,key='same-operation-1')
        self.assertNotEqual(a['workflowId'],b['workflowId'])
        self.assert_code('WORKFLOW_NOT_FOUND',lambda:self.s.run_workflow(self.b,'new-run-123',
            {'workflowId':a['workflowId'],'text':'anything'}))

    def test_racing_same_intent_executes_once(self):
        workflow=self.create()
        results=[]
        with ThreadPoolExecutor(max_workers=8) as pool:
            tasks=[pool.submit(self.sample_run,workflow,self.a,'same-race-123') for _ in range(8)]
            results=[t.result() for t in tasks]
        self.assertEqual(len({r['runId'] for r in results}),1)
        with managed_test_connection(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM runs').fetchone()[0],1)

    def test_replaying_old_workflow_update_after_new_revision(self):
        w=self.create()
        p={'workflowId':w['workflowId'],'title':'Second','expectedRevision':1,
           'maxKeywords':4,'minLength':2}
        v=self.s.update_workflow(self.a,'update-12345',p)
        self.assertEqual(v['revision'],2)
        self.assertEqual(self.s.update_workflow(self.a,'update-12345',p),v)
        self.assert_code('STALE_REVISION',lambda:self.s.update_workflow(self.a,'update-54321',p))
        self.assertEqual(self.sample_run(w)['revision'],2)

    def test_invalid_configuration_and_bounds_refused(self):
        self.assert_code('INVALID_GRAPH_CONFIG',lambda:self.s.create_workflow(self.a,'invalid-bool',
                       {'title':'Example','maxKeywords':True}))
        self.assert_code('INVALID_GRAPH_CONFIG',lambda:self.s.create_workflow(self.a,'invalid-qty',
                       {'title':'Example','maxKeywords':17}))
        self.assert_code('INVALID_TEXT',lambda:self.s.create_workflow(self.a,'invalid-name',{'title':''}))
        w=self.create()
        self.assert_code('INVALID_TEXT',lambda:self.s.run_workflow(self.a,'invalid-body',
                       {'workflowId':w['workflowId'],'text':'x'*4097}))

    def test_run_foreign_id_denied(self):
        r=self.sample_run()
        self.assert_code('RUN_NOT_FOUND',lambda:self.s.get_run(self.b,r['runId']))

    def test_cross_app_artifact_import_and_replay(self):
        r=self.sample_run()
        p={'title':'Saved keywords','sourceRunId':r['runId']}
        d=self.s.create_document(self.a,'import-key-123',p)
        self.assertEqual(self.s.create_document(self.a,'import-key-123',p),d)
        q=self.s.search(self.a,{'query':'evidence'})
        self.assertEqual(q['results'][0]['documentId'],d['documentId'])
        self.assertEqual(q['results'][0]['documentSha256'],d['sha256'])
        self.assert_code('SOURCE_RUN_NOT_FOUND',lambda:self.s.create_document(self.b,'foreign-doc-123',p))

    def test_retrieval_and_evaluation_survive_process_restart(self):
        d=self.s.create_document(self.a,'doc-create-123',{'title':'Doc','text':'delta epsilon evidence'})
        evaluator=ProofStore(self.path)
        out=evaluator.evaluate(self.a,'eval-key-123',
                               {'query':'epsilon','expectedDocumentId':d['documentId']})
        self.assertTrue(out['passed']); self.assertEqual(out['total'],1)
        self.assertEqual(evaluator.evaluate(self.a,'eval-key-123',
                           {'query':'epsilon','expectedDocumentId':d['documentId']}),out)
        self.assertEqual(len(ProofStore(self.path).list_evaluations(self.a)),1)

    def test_evaluation_failure_is_not_claimed_pass(self):
        d1=self.s.create_document(self.a,'doccreate1',{'title':'A','text':'alpha'})
        d2=self.s.create_document(self.a,'doccreate2',{'title':'B','text':'beta'})
        r=self.s.evaluate(self.a,'eval-key-999',{'query':'alpha','expectedDocumentId':d2['documentId']})
        self.assertFalse(r['passed']);self.assertEqual(r['correct'],0)
        self.assertEqual(r['observedDocumentId'],d1['documentId'])

    def test_edits_change_document_identity_and_old_corpus(self):
        d=self.s.create_document(self.a,'doc-start',{'title':'A','text':'omega alpha'})
        first=self.s.search(self.a,{'query':'omega'})
        p={'documentId':d['documentId'],'title':'A revised','text':'delta beta','expectedRevision':1}
        edit=self.s.update_document(self.a,'docedit1',p)
        self.assertNotEqual(d['sha256'],edit['sha256'])
        self.assertEqual(self.s.update_document(self.a,'docedit1',p),edit)
        self.assert_code('STALE_REVISION',lambda:self.s.update_document(self.a,'docedit2',p))
        self.assertEqual(self.s.search(self.a,{'query':'omega'})['results'],[])
        self.assertNotEqual(first['corpusSha256'],self.s.search(self.a,{'query':'omega'})['corpusSha256'])

    def test_document_deletion_removes_active_searchable_source(self):
        d=self.s.create_document(self.a,'doc-del-1',{'title':'A','text':'needle specialtoken'})
        self.assertTrue(self.s.search(self.a,{'query':'specialtoken'})['results'])
        payload={'documentId':d['documentId']}
        deleted=self.s.delete_document(self.a,'delete-key-1',payload)
        self.assertEqual(self.s.delete_document(self.a,'delete-key-1',payload),deleted)
        self.assertEqual(self.s.search(self.a,{'query':'specialtoken'})['results'],[])
        self.assert_code('DOCUMENT_NOT_FOUND',lambda:self.s.delete_document(self.a,'delete-key-2',payload))

    def test_bad_requests_unknown_or_duplicate_fields(self):
        self.assert_code('INVALID_FIELDS',lambda:self.s.create_workflow(self.a,'validkey-1',{'title':'X','unexpected':1}))
        self.assert_code('INVALID_FIELDS',lambda:self.s.search(self.a,{'query':'a','admin':True}))
        self.assert_code('INVALID_OPERATION_KEY',lambda:self.s.create_workflow(self.a,'bad',{'title':'A'}))
        self.assert_code('SESSION_REQUIRED',lambda:self.s.list_documents('not-a-bearer-capability'))

    def test_corpus_never_crosses_workspaces(self):
        self.s.create_document(self.a,'document-abc123',{'title':'Private demo A','text':'alpha only'})
        self.assertEqual(self.s.search(self.b,{'query':'alpha'})['results'],[])
        self.assertEqual(self.s.list_documents(self.b),[])

    def test_sql_injection_terms_are_plain_text(self):
        self.s.create_document(self.a,'safe-sql-001',{'title':'A','text':'query alpha'})
        self.assertEqual(self.s.search(self.a,{'query':'x\'; DROP TABLE documents; --'})['results'],[])
        self.assertEqual(len(self.s.list_documents(self.a)),1)

    def test_ascii_lexical_whole_tokens_and_grounded_excerpts(self):
        d=self.s.create_document(self.a,'tokens-abc123',{'title':'A','text':'the\ncartilage has a cart of tokens'})
        self.assertEqual(self.s.search(self.a,{'query':'car'})['results'],[])
        hits=self.s.search(self.a,{'query':'cart'})['results']
        self.assertEqual(hits[0]['documentId'],d['documentId'])
        self.assertIn('cart',hits[0]['snippet'])

    def test_invalid_cross_workspace_expected_document(self):
        d=self.s.create_document(self.a,'doc-expect1',{'title':'Only in A','text':'alpha'})
        self.assert_code('EXPECTED_DOCUMENT_NOT_FOUND',lambda:self.s.evaluate(self.b,'eval-foreign-1',
                {'query':'alpha','expectedDocumentId':d['documentId']}))


if __name__=='__main__': unittest.main()
