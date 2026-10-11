"""Hand-checkable synthetic rankings; no models, datasets or services accessed."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evaluation import evaluate, load_dataset

HERE = Path(__file__).resolve().parent


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((HERE / "synthetic.json").read_text())

    def test_hand_calculated_macro_metrics(self):
        report = evaluate(self.data, k=2)
        self.assertEqual(report["macro_recall_at_k"], 0.75)
        self.assertEqual(report["mrr_at_k"], 0.75)
        self.assertEqual(report["queries"][0]["recall_at_k"], 0.5)
        self.assertEqual(report["queries"][0]["reciprocal_rank_at_k"], 0.5)
        self.assertEqual(report["query_count"], 2)

    def test_cutoff_changes_recall_not_first_hit(self):
        report = evaluate(self.data, k=3)
        self.assertEqual(report["macro_recall_at_k"], 1.0)
        self.assertEqual(report["mrr_at_k"], 0.75)

    def test_empty_results_contribute_zero_instead_of_disappearing(self):
        self.data["queries"][1]["retrieved"] = []
        report = evaluate(self.data, k=2)
        self.assertEqual(report["query_count"], 2)
        self.assertEqual(report["mrr_at_k"], 0.25)
        self.assertEqual(report["macro_recall_at_k"], 0.25)

    def test_repeatability_fingerprint_and_input_preservation(self):
        before = copy.deepcopy(self.data)
        one = evaluate(self.data, k=2)
        two = evaluate(copy.deepcopy(self.data), k=2)
        self.assertEqual(one, two)
        self.assertEqual(self.data, before)
        self.assertEqual(len(one["dataset_sha256"]), 64)
        self.data["queries"][0]["retrieved"].reverse()
        self.assertNotEqual(one["dataset_sha256"], evaluate(self.data, k=2)["dataset_sha256"])

    def test_duplicate_query_ids_are_rejected(self):
        self.data["queries"].append(copy.deepcopy(self.data["queries"][0]))
        with self.assertRaises(ValueError): evaluate(self.data, k=2)

    def test_duplicate_ranked_documents_after_cutoff_are_also_rejected(self):
        self.data["queries"][0]["retrieved"].append("d-a")
        with self.assertRaises(ValueError): evaluate(self.data, k=1)

    def test_duplicate_corpus_labels_and_relevance_labels_are_rejected(self):
        for field in ["corpus", "relevant", "training_query_ids"]:
            data = copy.deepcopy(self.data)
            values = data["queries"][0][field] if field == "relevant" else data[field]
            values.append(values[0])
            with self.subTest(field=field), self.assertRaises(ValueError): evaluate(data, k=2)

    def test_unknown_document_ids_are_rejected(self):
        for field in ["relevant", "retrieved"]:
            data = copy.deepcopy(self.data)
            data["queries"][0][field].append("not-in-corpus")
            with self.subTest(field=field), self.assertRaises(ValueError): evaluate(data, k=2)

    def test_identifier_overlap_between_training_and_evaluation_is_rejected(self):
        self.data["training_query_ids"].append("q-alpha")
        with self.assertRaises(ValueError): evaluate(self.data, k=2)

    def test_no_relevance_labels_is_error_not_perfect_score(self):
        self.data["queries"][0]["relevant"] = []
        with self.assertRaises(ValueError): evaluate(self.data, k=2)

    def test_empty_evaluation_and_unknown_fields_are_rejected(self):
        for update in [{"queries": []}, {"corpus": []}, {"schema": "unknown"}, {"typo": 1}]:
            data = copy.deepcopy(self.data); data.update(update)
            with self.subTest(update=list(update)), self.assertRaises(ValueError): evaluate(data, k=2)

    def test_wrong_types_and_invalid_cutoffs_are_rejected(self):
        for k in [True, 0, -1, 101, 2.5, "2"]:
            with self.subTest(k=k), self.assertRaises(ValueError): evaluate(self.data, k=k)
        for data in [[], None, "wrong", {**self.data, "queries": {}}]:
            with self.subTest(data_type=type(data).__name__), self.assertRaises(ValueError): evaluate(data, k=2)

    def test_loader_rejects_duplicate_keys_nonfinite_values_and_oversize(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            for text in ['{"schema":1,"schema":2}', '{"x":NaN}', " " * 65537]:
                path.write_text(text)
                with self.subTest(length=len(text)), self.assertRaises(ValueError): load_dataset(path)

    def test_cli_prints_real_computed_result_and_returns_nonzero_on_invalid_data(self):
        command = [sys.executable, "-B", str(HERE / "evaluation.py")]
        result = subprocess.run(command + [str(HERE / "synthetic.json"), "--k", "2"], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["mrr_at_k"], 0.75)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"; path.write_text("{}")
            result = subprocess.run(command + [str(path)], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")

    def test_direct_api_rejects_excessive_total_identifier_references(self):
        corpus = list("abcdefghijklmnopqrstuvwxyz")
        data = {"schema": "ranking-eval.v1", "corpus": corpus, "training_query_ids": [],
                "queries": [{"id": f"q{i}", "relevant": ["a"], "retrieved": corpus} for i in range(200)]}
        self.assertLess(len(json.dumps(data).encode()), 65536)
        with self.assertRaises(ValueError): evaluate(data, k=2)


if __name__ == "__main__":
    unittest.main()
