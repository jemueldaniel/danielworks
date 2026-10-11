"""Actual SQLite migration, rollback, drift and concurrent writer tests."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3,tempfile,unittest
from migration import Gate,define,MigrationError
class MigrationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="safe-migrate-")
        self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"test.sqlite"
        self.gate=Gate(self.path)
        self.a=define("create_records","CREATE TABLE records (id INTEGER PRIMARY KEY,label TEXT NOT NULL)")
        self.b=define("create_index","CREATE INDEX records_label ON records(label)")
    def test_apply(self):
        self.assertEqual(self.gate.apply([self.a])["new"],["create_records"])
    def test_replay_noop(self):
        self.gate.apply([self.a]);self.assertEqual(self.gate.apply([self.a])["applied_count"],0)
    def test_two_changes(self):
        self.assertEqual(self.gate.apply([self.a,self.b])["applied_count"],2)
    def test_append_only(self):
        self.gate.apply([self.a]);self.assertEqual(self.gate.apply([self.a,self.b])["new"],["create_index"])
    def test_historical_edit(self):
        self.gate.apply([self.a])
        with self.assertRaisesRegex(MigrationError,"historical_change_drift"):
            self.gate.apply([define("create_records","CREATE TABLE changed(id INT)")])
    def test_historical_rename(self):
        self.gate.apply([self.a])
        with self.assertRaisesRegex(MigrationError,"historical_change_drift"):
            self.gate.apply([define("new_name",self.a.sql)])
    def test_missing_history(self):
        self.gate.apply([self.a,self.b])
        with self.assertRaisesRegex(MigrationError,"missing_historical_changes"):
            self.gate.apply([self.a])
    def test_rollback_sql(self):
        bad=define("bad_step","CREATE TABLE records (x INT)")
        with self.assertRaisesRegex(MigrationError,"sql_execution_failed"):
            self.gate.apply([self.a,bad])
        self.assertEqual(self.gate.version(),[])
    def test_storage_tampering(self):
        self.gate.apply([self.a])
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute("UPDATE _public_migrations SET sha256=?",("0"*64,))
        with self.assertRaisesRegex(MigrationError,"historical_change_drift"):
            self.gate.apply([self.a])
    def test_forged_hash(self):
        fake=type(self.a)(self.a.key,self.a.sql,"0"*64)
        with self.assertRaisesRegex(MigrationError,"invalid_change_digest"):
            self.gate.apply([fake])
    def test_duplicate(self):
        with self.assertRaisesRegex(MigrationError,"duplicate_change_id"):
            self.gate.apply([self.a,self.a])
    def test_bad_ids(self):
        for bad in ("","../oops","a b","Upper","x"*50,42):
            with self.subTest(bad=bad),self.assertRaises(MigrationError):
                define(bad,"SELECT 1")
    def test_bad_sql(self):
        for sql in ("","\x00",11,"z"*10001):
            with self.subTest(sql=str(sql)[:4]),self.assertRaises(MigrationError):
                define("bad_sql",sql)
    def test_two_statements_fail_atomically(self):
        bad=define("two","CREATE TABLE one(id INT);CREATE TABLE two(id INT)")
        with self.assertRaisesRegex(MigrationError,"sql_execution_failed"):
            self.gate.apply([bad])
        self.assertEqual(self.gate.version(),[])
    def test_redacted_sql_errors(self):
        with self.assertRaises(MigrationError) as caught:
            self.gate.apply([define("syntax_fail","NOT AN ACTUAL DATABASE QUERY")])
        self.assertEqual(str(caught.exception),"sql_execution_failed")
    def test_concurrent_replay(self):
        def run(_):return self.gate.apply([self.a])["applied_count"]
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(run,range(12)))
        self.assertEqual(sum(results),1)
    def test_empty_plan(self):
        with self.assertRaisesRegex(MigrationError,"invalid_plan"):self.gate.apply([])
    def test_untyped_plan(self):
        with self.assertRaisesRegex(MigrationError,"invalid_plan"):
            self.gate.apply([{"key":"oops"}])
    def test_resume_process(self):
        self.gate.apply([self.a])
        self.assertEqual(Gate(self.path).apply([self.a,self.b])["new"],["create_index"])
    def test_plan_string_rejected(self):
        with self.assertRaisesRegex(MigrationError,"invalid_plan"):
            self.gate.apply("DROP TABLE users")
    def test_bool_sql(self):
        with self.assertRaisesRegex(MigrationError,"invalid_sql"):define("bad_sql",True)
    def test_plan_capacity(self):
        changes=[define("step_"+str(i),"SELECT 1") for i in range(101)]
        with self.assertRaisesRegex(MigrationError,"invalid_plan"):self.gate.apply(changes)
if __name__=="__main__":unittest.main()
