"""Real SQLite tests. Clock injection is identified separately from wall-clock recovery."""
import concurrent.futures
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from workbench import Store, InvalidInput, CheckpointError

class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'work.sqlite3'
        self.tick = 1000
        self.store = Store(self.db, clock=lambda: self.tick)
    def tearDown(self):
        self.tmp.cleanup()
    def create(self, key='run-one', engine='fts5', tenant='demo'):
        return self.store.submit(tenant, {'key': key, 'engine': engine, 'k': 2})
    def test_connection_is_closed_after_scope(self):
        with self.store._connect() as db:
            self.assertEqual(db.execute('SELECT 1').fetchone()[0], 1)
        with self.assertRaises(sqlite3.ProgrammingError): db.execute('SELECT 1')
    def test_submit_is_a_persistent_record(self):
        self.assertIsInstance(self.create(), dict)
        self.assertEqual(Store(self.db).inspect('demo', 'run-one')['state'], 'pending')
    def test_idempotency_conflict_keeps_original(self):
        self.create(); self.create()
        self.assertEqual(len(self.store.list('demo')['items']), 1)
        with self.assertRaises(InvalidInput): self.create(engine='lexical')
        self.assertEqual(self.store.inspect('demo', 'run-one')['engine'], 'fts5')
    def test_strict_input_and_bounds(self):
        for value in [{'key':'UPPER','engine':'fts5','k':2}, {'key':'ok','engine':'fts5','k':True},
                      {'key':'ok','engine':'fts5','k':0}, {'key':'ok','engine':'shell','k':2},
                      {'key':'ok','engine':'fts5','k':2,'tenant':'other'}]:
            with self.subTest(value=value), self.assertRaises(InvalidInput): self.store.submit('demo', value)
        self.assertEqual(self.store.list('demo')['items'], [])
    def test_real_fts5_and_preserved_grader(self):
        self.create(); result=self.store.work('demo')['job']
        self.assertEqual(result['state'], 'done')
        self.assertEqual(result['result']['mrr_at_k'], 0.8)
        self.assertEqual(result['result']['macro_recall_at_k'], 0.8)
        self.assertEqual(result['result']['failures'][0]['id'], 'q-synonym')
        self.assertEqual(result['result']['failures'][0]['retrieved'], [])
        self.assertEqual(result['checkpoint_count'], 5)
    def test_preserved_lexical_baseline_is_executed(self):
        self.create(engine='lexical'); result=self.store.work('demo')['job']['result']
        self.assertEqual(result['mrr_at_k'], 0.8)
        self.assertEqual(result['failures'][0]['retrieved'], ['alpha','beta'])
    def test_tenant_partition_uses_real_database(self):
        self.create(); self.create(tenant='other', engine='lexical')
        self.store.cancel('other', 'run-one')
        self.assertEqual(self.store.inspect('demo', 'run-one')['state'], 'pending')
        self.assertEqual(self.store.inspect('other', 'run-one')['state'], 'cancelled')
        self.assertIsNone(self.store.inspect('third', 'run-one'))
        self.assertEqual(self.store.list('third')['items'], [])
    def test_keyset_pagination_is_stable_and_bounded(self):
        for i in range(5): self.create(key=f'run-{i}')
        one=self.store.list('demo', limit=2)
        two=self.store.list('demo', limit=2, cursor=one['next_cursor'])
        self.assertEqual([x['key'] for x in one['items']+two['items']], ['run-0','run-1','run-2','run-3'])
        for limit in (0,21,True):
            with self.assertRaises(InvalidInput): self.store.list('demo', limit=limit)
        with self.assertRaises(InvalidInput): self.store.list('demo', cursor="' OR 1=1")
    def test_checkpoint_resume_fences_old_generation(self):
        self.create(); partial=self.store.work('demo', max_cases=2, lease_ms=100)['job']
        self.assertEqual(partial['state'], 'running'); self.assertEqual(partial['checkpoint_count'], 2)
        self.assertIsNone(self.store.work('demo')['job'])
        self.tick+=101
        final=self.store.work('demo')['job']
        self.assertEqual(final['state'], 'done'); self.assertEqual(final['attempts'], 2)
        self.assertEqual(final['checkpoint_count'], 5)
        self.assertEqual(final['result']['resumed_cases'], 2)
    def test_cancel_mid_run_fences_completion(self):
        self.create()
        def observer(event):
            if event['event']=='checkpoint': self.store.cancel('demo','run-one')
        final=self.store.work('demo', observer=observer)['job']
        self.assertEqual(final['state'], 'cancelled'); self.assertIsNone(final['result'])
        self.assertEqual(final['checkpoint_count'], 1)
    def test_corrupt_checkpoint_fails_closed(self):
        self.create(); self.store.work('demo', max_cases=1, lease_ms=100)
        with closing(sqlite3.connect(self.db)) as db:
            db.execute("UPDATE checkpoints SET ranking='[\"delta\"]'")
            db.commit()
        self.tick+=101
        with self.assertRaises(CheckpointError): self.store.work('demo')
        self.assertIsNone(self.store.inspect('demo','run-one')['result'])
    def test_concurrent_idempotent_submission(self):
        def submit(_): return Store(self.db).submit('demo', {'key':'race','engine':'fts5','k':2})
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(submit,range(8)))
        self.assertTrue(all(x['key']=='race' for x in results))
        self.assertEqual(len(self.store.list('demo')['items']),1)
    def test_parallel_workers_execute_one_lease(self):
        self.create()
        def work(_): return Store(self.db,clock=lambda:1000).work('demo')
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(work,range(4)))
        self.assertEqual(sum(x['job'] is not None for x in results),1)
        self.assertEqual(self.store.inspect('demo','run-one')['attempts'],1)
    def test_no_implicit_replay_of_terminal_job(self):
        self.create(); self.store.work('demo'); self.create()
        self.assertIsNone(self.store.work('demo')['job'])
        self.assertFalse(self.store.cancel('demo','run-one'))
    def test_search_quotes_user_terms_not_fts_operators(self):
        self.assertEqual(self.store.search('password',2)[0]['id'],'alpha')
        self.assertEqual(self.store.search('" OR *',2), [])
        with self.assertRaises(InvalidInput): self.store.search('x'*501,2)

if __name__=='__main__': unittest.main()
