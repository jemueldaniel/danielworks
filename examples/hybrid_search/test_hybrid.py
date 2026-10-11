"""Actual SQLite FTS5, ranking, revision, isolation and retrieval-metric regressions."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from hybrid import HybridSearch, SearchError, DIMENSIONS, _vector, _terms


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"hybrid.sqlite"
        self.db=HybridSearch(self.path)
        self.db.put("tenant-a","alpha-doc","Database isolation","SQLite transactions and tenant isolation",version=1)
        self.db.put("tenant-a","beta-doc","Model evaluation","Ranking recall precision and model evaluation",version=1)
        self.db.put("tenant-a","gamma-doc","API reliability","Idempotency and retry handling",version=1)

    def ids(self, query, **kw):
        return [r["document_id"] for r in self.db.search("tenant-a",query,**kw)]

    def test_fts_matches_real_indexed_document(self):
        self.assertEqual(self.ids("sqlite"),["alpha-doc"])

    def test_scored_results_include_two_rank_sources(self):
        result=self.db.search("tenant-a","model")
        self.assertEqual(result[0]["document_id"],"beta-doc")
        self.assertEqual(result[0]["lexical_rank"],1)
        self.assertEqual(result[0]["hashed_token_rank"],1)
        self.assertGreater(result[0]["score"],0)

    def test_no_match_never_invents_semantic_answer(self):
        self.assertEqual(self.ids("unicorn"),[])

    def test_query_binds_tenant_before_return(self):
        self.db.put("tenant-b","secret-doc","Sensitive sample","Unicorn transactions",version=1)
        self.assertEqual(self.db.search("tenant-a","unicorn"),[])
        self.assertEqual([x["document_id"] for x in self.db.search("tenant-b","unicorn")],["secret-doc"])

    def test_same_id_in_multiple_tenants_is_partitioned(self):
        self.db.put("tenant-b","alpha-doc","Other","Secret rainbow",version=1)
        self.assertEqual(self.ids("secret"),[])
        self.assertEqual([x["title"] for x in self.db.search("tenant-b","rainbow")],["Other"])

    def test_revision_update_refreshes_fts(self):
        self.assertEqual(self.db.put("tenant-a","alpha-doc","Updated","New planetary data",version=2),"updated")
        self.assertEqual(self.ids("sqlite"),[])
        self.assertEqual(self.ids("planetary"),["alpha-doc"])

    def test_equal_version_and_identical_bytes_is_idempotent(self):
        self.assertEqual(self.db.put("tenant-a","alpha-doc","Database isolation",
                                     "SQLite transactions and tenant isolation",version=1),"unchanged")
        self.assertEqual(self.db.audit("tenant-a")["tenant_documents"],3)

    def test_equal_version_and_different_body_fails(self):
        with self.assertRaisesRegex(SearchError,"revision_conflict"):
            self.db.put("tenant-a","alpha-doc","Database isolation","mutated",version=1)
        self.assertEqual(self.ids("sqlite"),["alpha-doc"])

    def test_skipped_revision_fails(self):
        with self.assertRaisesRegex(SearchError,"revision_conflict"):
            self.db.put("tenant-a","alpha-doc","Changed","body",version=3)

    def test_new_document_requires_version_one(self):
        with self.assertRaisesRegex(SearchError,"revision_conflict"):
            self.db.put("tenant-a","new-doc","Title","data",version=2)

    def test_delete_revision_fence_blocks_stale_request(self):
        with self.assertRaisesRegex(SearchError,"revision_conflict"):
            self.db.delete("tenant-a","alpha-doc",expected_version=2)
        self.assertEqual(self.ids("sqlite"),["alpha-doc"])

    def test_delete_removes_both_canonical_and_fts(self):
        self.assertEqual(self.db.delete("tenant-a","alpha-doc",expected_version=1),"deleted")
        self.assertEqual(self.ids("sqlite"),[])
        self.assertEqual(self.db.audit("tenant-a")["tenant_documents"],2)

    def test_cross_tenant_delete_fails(self):
        with self.assertRaisesRegex(SearchError,"document_not_found"):
            self.db.delete("tenant-b","alpha-doc",expected_version=1)
        self.assertEqual(self.ids("sqlite"),["alpha-doc"])

    def test_reopened_database_has_same_ranking(self):
        before=self.db.search("tenant-a","ranking")
        again=HybridSearch(self.path).search("tenant-a","ranking")
        self.assertEqual(before,again)

    def test_search_result_order_is_deterministic(self):
        a=self.db.search("tenant-a","tenant model")
        for _ in range(5):
            self.assertEqual(self.db.search("tenant-a","tenant model"),a)

    def test_corpus_and_index_consistency_audit(self):
        self.assertEqual(self.db.audit("tenant-a")["status"],"PASS")

    def test_missing_fts_row_is_detected(self):
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute("DELETE FROM search_index WHERE rowid=(SELECT pk FROM documents WHERE tenant=? AND document_id=?)",
                        ("tenant-a","alpha-doc"))
        with self.assertRaisesRegex(SearchError,"index_drift"):
            self.db.audit("tenant-a")

    def test_modified_fts_row_is_detected(self):
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute("UPDATE search_index SET title=? WHERE rowid=(SELECT pk FROM documents WHERE document_id=?)",
                        ("Changed","alpha-doc"))
        with self.assertRaisesRegex(SearchError,"index_drift"):
            self.db.audit("tenant-a")

    def test_modified_canonical_row_is_detected(self):
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute("UPDATE documents SET body=? WHERE document_id=?",("changed","alpha-doc"))
        with self.assertRaisesRegex(SearchError,"index_drift"):
            self.db.audit("tenant-a")

    def test_sanitized_query_treats_fts_operators_as_text(self):
        query='sqlite" OR "other" NEAR(tenant)'
        result=self.db.search("tenant-a",query)
        self.assertTrue(all(r["document_id"] in {"alpha-doc","beta-doc","gamma-doc"} for r in result))
        self.assertIn("alpha-doc",[r["document_id"] for r in result])

    def test_sql_injection_string_never_changes_database(self):
        self.db.search("tenant-a", "foo' ; DROP TABLE documents; --")
        self.assertEqual(self.db.audit("tenant-a")["tenant_documents"],3)

    def test_untrusted_html_is_returned_as_data_not_executed(self):
        body="<script>alert(1)</script> database"
        self.db.put("tenant-a","unsafe-doc","HTML payload",body,version=1)
        result=self.db.search("tenant-a","database")
        self.assertTrue(any("<script>" in r["snippet"] for r in result if r["document_id"]=="unsafe-doc"))
        self.assertEqual(self.db.audit("tenant-a")["status"],"PASS")

    def test_top_k_restricts_return_size(self):
        r=self.db.search("tenant-a","model transactions reliability",top_k=1)
        self.assertEqual(len(r),1)

    def test_malformed_top_k_and_bool_rejected(self):
        for k in (0,21,True,1.3,"5"):
            with self.subTest(k=k),self.assertRaisesRegex(SearchError,"invalid_k"):
                self.db.search("tenant-a","model",top_k=k)

    def test_empty_punctuation_only_and_too_many_terms_rejected(self):
        for q in ("!!!", "a", "a "*13,"x "*13):
            with self.subTest(q=q),self.assertRaisesRegex(SearchError,"invalid_query_terms"):
                self.db.search("tenant-a",q)

    def test_long_body_and_nontext_rejected(self):
        for body in ("z"*4001,True,123,""):
            with self.subTest(value=str(body)[:5]),self.assertRaisesRegex(SearchError,"invalid_text"):
                self.db.put("tenant-a","bad-doc","Title",body,version=1)

    def test_invalid_tenant_and_document_identifiers_rejected(self):
        for invalid in ("", "../tenant", "a\n", "tenant a","Aupper",21):
            with self.subTest(value=invalid),self.assertRaises(SearchError):
                self.db.search(invalid,"model")
        with self.assertRaises(SearchError):
            self.db.put("tenant-a","bad/id","Title","Text",version=1)

    def test_invalid_versions_rejected(self):
        for version in (-1,0,True,1.1,2**31):
            with self.subTest(version=version),self.assertRaisesRegex(SearchError,"invalid_version"):
                self.db.put("tenant-a","fresh-doc","Title","Body",version=version)

    def test_hashed_lexical_vector_is_repeatable_and_bounded(self):
        v=_vector(_terms("Model model routing"))
        self.assertEqual(len(v),DIMENSIONS)
        self.assertEqual(v,_vector(_terms("Model model routing")))
        self.assertAlmostEqual(sum(x*x for x in v),1.0)

    def test_perfect_synthetic_retrieval_quality(self):
        rows=[
            {"query":"sqlite transactions","expected":["alpha-doc"]},
            {"query":"ranking recall","expected":["beta-doc"]},
            {"query":"retry handling","expected":["gamma-doc"]},
        ]
        report=self.db.evaluate("tenant-a",rows,top_k=1)
        self.assertEqual(report["recall_at_k"],1.0)
        self.assertEqual(report["mrr_at_k"],1.0)
        self.assertEqual(report["ndcg_at_k"],1.0)
        self.assertEqual(report["cases"],3)

    def test_missing_retrieval_is_honestly_zero(self):
        report=self.db.evaluate("tenant-a",[{"query":"unicorn","expected":["alpha-doc"]}],top_k=1)
        self.assertEqual(report["recall_at_k"],0.0)
        self.assertEqual(report["mrr_at_k"],0.0)
        self.assertEqual(report["ndcg_at_k"],0.0)

    def test_expected_duplicate_and_wrong_case_schemas_fail(self):
        for cases in ([{"query":"model","expected":["beta-doc","beta-doc"]}],
                      [{"query":"model"}],
                      [{"query":"model","expected":[]}]):
            with self.subTest(cases=cases),self.assertRaises(SearchError):
                self.db.evaluate("tenant-a",cases)

    def test_empty_case_list_rejected(self):
        with self.assertRaisesRegex(SearchError,"invalid_cases"):
            self.db.evaluate("tenant-a",[])

    def test_concurrent_create_with_same_revision_is_safe(self):
        def worker(_):
            return self.db.put("tenant-a","concurrent-doc","Concurrent indexing",
                               "SQLite retrieval supports concurrent writers",version=1)
        with ThreadPoolExecutor(max_workers=6) as pool:
            statuses=list(pool.map(worker,range(12)))
        self.assertEqual(statuses.count("created"),1)
        self.assertEqual(statuses.count("unchanged"),11)
        self.assertEqual(self.ids("concurrent"),["concurrent-doc"])
        self.assertEqual(self.db.audit("tenant-a")["tenant_documents"],4)

    def test_sequential_version_fence_is_monotonic(self):
        for version in range(2,9):
            self.db.put("tenant-a","alpha-doc","Revision tracking","Version "+str(version),version=version)
        with self.assertRaisesRegex(SearchError,"revision_conflict"):
            self.db.put("tenant-a","alpha-doc","Stale","stale",version=3)
        self.assertEqual(self.db.audit("tenant-a")["tenant_documents"],3)


if __name__=="__main__":
    unittest.main()
