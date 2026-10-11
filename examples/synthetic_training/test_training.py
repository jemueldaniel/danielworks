"""Real optimizer, validation leakage, bounded inputs, interruption and integrity tests."""
import copy
import json
import math
import unittest
from dataclasses import replace

from training import Config, Row, _checkpoint, fit_standardizer, report, split_indices, synthetic_rows, train, validate_rows


class TrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = synthetic_rows()
        cls.config = Config()
        cls.complete = train(cls.rows, cls.config)

    def test_generator_is_deterministic_balanced_and_seeded(self):
        self.assertEqual(self.rows, synthetic_rows())
        self.assertNotEqual(self.rows, synthetic_rows(seed=99))
        self.assertEqual([sum(r.label == y for r in self.rows) for y in (0, 1)], [200, 200])

    def test_stratified_splits_disjoint_and_deterministic(self):
        parts = split_indices(self.rows, self.config.seed)
        self.assertEqual(parts, split_indices(self.rows, self.config.seed))
        self.assertEqual({k: len(v) for k, v in parts.items()}, {'train': 240, 'validation': 80, 'test': 80})
        self.assertEqual(len(set(sum((list(v) for v in parts.values()), []))), len(self.rows))
        self.assertTrue(all(sum(self.rows[i].label for i in part) * 2 == len(part) for part in parts.values()))

    def test_preprocessing_fits_train_only(self):
        parts = split_indices(self.rows, self.config.seed)
        old = fit_standardizer(self.rows, parts['train'])
        test_id = parts['test'][0]
        alt = list(self.rows)
        alt[test_id] = Row((9999., -9999., 4444.), alt[test_id].label)
        self.assertEqual(old, fit_standardizer(tuple(alt), parts['train']))
        self.assertNotEqual(old, fit_standardizer(tuple(alt), parts['test']))

    def test_finite_optimizer_converges_above_majority_baseline(self):
        result = report(self.rows, self.config, self.complete)
        self.assertTrue(self.complete['finished'])
        self.assertGreater(result['test']['accuracy'], result['test_majority_baseline_accuracy'] + .15)
        self.assertLess(result['validation']['loss'], .5)
        self.assertTrue(math.isfinite(result['test']['loss']))
        self.assertEqual(sum(result['samples'].values()), len(self.rows))
        self.assertEqual(result['training_type'], 'real_cpu_optimizer')

    def test_deterministic_repeat_training(self):
        self.assertEqual(train(self.rows, self.config), self.complete)

    def test_interruption_roundtrip_resumes_identical_state(self):
        partial = train(self.rows, self.config, stop_after_epoch=9)
        self.assertEqual(partial['next_epoch'], 9)
        self.assertFalse(partial['finished'])
        decoded = json.loads(json.dumps(partial))
        self.assertEqual(train(self.rows, self.config, checkpoint=decoded), self.complete)

    def test_checkpoint_not_mutated_by_resuming(self):
        partial = train(self.rows, self.config, stop_after_epoch=3)
        snapshot = copy.deepcopy(partial)
        train(self.rows, self.config, checkpoint=partial, stop_after_epoch=4)
        self.assertEqual(partial, snapshot)

    def test_rejects_modified_training_data_without_silent_replay(self):
        altered = list(self.rows)
        altered[0] = Row((.5, .5, .5), altered[0].label)
        with self.assertRaisesRegex(ValueError, 'source/config mismatch'):
            train(tuple(altered), self.config, self.complete)

    def test_rejects_config_drift_without_replaying_checkpoint(self):
        with self.assertRaisesRegex(ValueError, 'source/config mismatch'):
            train(self.rows, replace(self.config, learning_rate=.1), self.complete)

    def test_rejects_tampered_checkpoint_checksum(self):
        bad = copy.deepcopy(self.complete)
        bad['weights'][0] = bad['weights'][0] + .01
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            train(self.rows, self.config, bad)

    def test_rejects_forged_progress_even_if_checksum_recomputed(self):
        bad = copy.deepcopy(self.complete)
        bad['next_epoch'] = 0
        bad['best_epoch'] = 0
        bad = _checkpoint({k: v for k, v in bad.items() if k != 'sha256'})
        with self.assertRaisesRegex(ValueError, 'completed state'):
            train(self.rows, self.config, bad)

    def test_rejects_early_completion_flag_even_when_checksum_recomputed(self):
        partial = train(self.rows, self.config, stop_after_epoch=7)
        bad = copy.deepcopy(partial)
        bad['finished'] = True
        bad = _checkpoint({k: v for k, v in bad.items() if k != 'sha256'})
        with self.assertRaisesRegex(ValueError, 'completion flag'):
            train(self.rows, self.config, bad)

    def test_rejects_unknown_checkpoint_field_and_nonfinite_weights(self):
        bad = copy.deepcopy(self.complete)
        bad['extra'] = 'oops'
        with self.assertRaises(ValueError): train(self.rows, self.config, bad)
        bad = copy.deepcopy(self.complete)
        bad['weights'][0] = float('nan')
        with self.assertRaises(ValueError): train(self.rows, self.config, bad)

    def test_rejects_invalid_rows_and_nan_features(self):
        altered = list(self.rows)
        altered[0] = Row((float('nan'), 0, 0), 0)
        with self.assertRaises(ValueError): validate_rows(tuple(altered))
        altered[0] = Row((0, 0, 0), True)
        with self.assertRaises(ValueError): validate_rows(tuple(altered))

    def test_refuses_invalid_hyperparameters_and_training_budget(self):
        for kwargs in ({'seed': True}, {'epochs': 0}, {'epochs': 999999}, {'batch_size': 0},
                       {'patience': 0}, {'learning_rate': 0}, {'learning_rate': float('nan')},
                       {'l2': -.1}, {'gradient_clip': math.inf}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError): Config(**kwargs)
        with self.assertRaises(ValueError): train(self.rows, self.config, stop_after_epoch=-1)

    def test_requires_completed_model_for_held_out_test_report(self):
        partial = train(self.rows, self.config, stop_after_epoch=2)
        with self.assertRaisesRegex(ValueError, 'not complete'):
            report(self.rows, self.config, partial)

    def test_replaying_completed_checkpoint_does_not_update_it(self):
        self.assertEqual(train(self.rows, self.config, self.complete), self.complete)


if __name__ == '__main__':
    unittest.main()
