"""Real child-process termination and wall-clock lease recovery, not a fake queue."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from workbench import Store, CheckpointError

class ProcessRecoveryTests(unittest.TestCase):
    def test_abrupt_worker_exit_preserves_checkpoint_then_reclaims_expired_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            database=Path(directory)/'process.sqlite3'
            store=Store(database)
            store.submit('demo',{'key':'crash-resume','engine':'fts5','k':2})
            # Explicit fault injection at the persisted-checkpoint boundary. os._exit
            # skips Python cleanup, unlike orderly Store/connection shutdown.
            code='''import os,sys,json
from workbench import Store
def crash(event):
    if event['event']=='checkpoint':
        print(json.dumps(event),flush=True)
        os._exit(70)
Store(sys.argv[1]).work('demo',lease_ms=600,observer=crash)
'''
            result=subprocess.run([sys.executable,'-B','-c',code,str(database)],cwd=Path(__file__).parent,
                                  capture_output=True,text=True,timeout=8)
            self.assertEqual(result.returncode,70,result.stderr)
            self.assertEqual(json.loads(result.stdout)['event'],'checkpoint')
            partial=Store(database).inspect('demo','crash-resume')
            self.assertEqual(partial['state'],'running')
            self.assertEqual(partial['checkpoint_count'],1)
            time.sleep(0.7)  # real wall-clock expiry, bounded to less than a second
            resumed=Store(database).work('demo')['job']
            self.assertEqual(resumed['state'],'done')
            self.assertEqual(resumed['attempts'],2)
            self.assertEqual(resumed['result']['resumed_cases'],1)
            self.assertEqual(resumed['result']['mrr_at_k'],0.8)
            self.assertIsNone(Store(database).work('demo')['job'])
    def test_unknown_schema_is_refused_without_rewriting_version(self):
        with tempfile.TemporaryDirectory() as directory:
            database=Path(directory)/'schema.sqlite3';Store(database)
            with closing(sqlite3.connect(database)) as db:
                db.execute('PRAGMA user_version=9');db.commit()
            with self.assertRaisesRegex(CheckpointError,'unknown_database_version'):Store(database)
            with closing(sqlite3.connect(database)) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],9)
    def test_persisted_input_identity_drift_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            database=Path(directory)/'input.sqlite3';Store(database)
            with closing(sqlite3.connect(database)) as db:
                db.execute("UPDATE workbench_meta SET value=? WHERE key='input_digest'",('0'*64,));db.commit()
            with self.assertRaises(CheckpointError):Store(database)

if __name__=='__main__':unittest.main()
