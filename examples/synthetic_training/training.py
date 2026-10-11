"""Deterministic, CPU-only classification; the supplied demo uses synthetic data.

No external network, credentials or packages. The demo uses no private data; this is real
optimization run, not evidence of training an LLM or using GPUs/distributed compute.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import random
from typing import NamedTuple

_FEATURES = 3
_VERSION = 1


class Row(NamedTuple):
    features: tuple[float, float, float]
    label: int


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _strict_int(value: object, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _finite_number(value: object, maximum: float = 1e12) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and abs(value) <= maximum


@dataclass(frozen=True)
class Config:
    epochs: int = 70
    learning_rate: float = 0.18
    batch_size: int = 16
    seed: int = 381
    l2: float = 0.002
    patience: int = 16
    gradient_clip: float = 4.0

    def __post_init__(self) -> None:
        if not _strict_int(self.epochs, 1, 1000) or not _strict_int(self.batch_size, 1, 256):
            raise ValueError('invalid training budget')
        if not _strict_int(self.seed, 0, 2**32 - 1) or not _strict_int(self.patience, 1, 1000):
            raise ValueError('invalid seed or patience')
        if not (_finite_number(self.learning_rate, 10) and 0 < self.learning_rate <= 1):
            raise ValueError('invalid learning rate')
        if not (_finite_number(self.l2, 1) and 0 <= self.l2 <= 1):
            raise ValueError('invalid regularizer')
        if not (_finite_number(self.gradient_clip, 1e4) and 0 < self.gradient_clip <= 1e4):
            raise ValueError('invalid clipping threshold')


def synthetic_rows(seed: int = 71, per_class: int = 200) -> tuple[Row, ...]:
    """Generate a versioned toy set, never reading disks or user information."""
    if not _strict_int(seed, 0, 2**32 - 1) or not _strict_int(per_class, 25, 1000):
        raise ValueError('invalid data budget')
    rng = random.Random(seed)
    rows = []
    for label in (0, 1):
        sign = 1 if label else -1
        for _ in range(per_class):
            vals = (rng.gauss(sign * 1.1, 0.95), rng.gauss(sign * 0.9, 1.05), rng.gauss(0, 1.1))
            rows.append(Row(vals, label))
    return tuple(rows)


def validate_rows(rows: tuple[Row, ...]) -> None:
    if not isinstance(rows, tuple) or not 50 <= len(rows) <= 2000:
        raise ValueError('invalid dataset size')
    counts = [0, 0]
    for r in rows:
        if not isinstance(r, Row) or len(r.features) != _FEATURES or type(r.label) is not int or r.label not in (0, 1):
            raise ValueError('invalid row')
        if not all(_finite_number(n, 1e6) for n in r.features):
            raise ValueError('invalid feature')
        counts[r.label] += 1
    if min(counts) < 25:
        raise ValueError('insufficient class support')


def split_indices(rows: tuple[Row, ...], seed: int) -> dict[str, tuple[int, ...]]:
    """Stratified independent 60/20/20 split with no overlapping IDs."""
    validate_rows(rows)
    if not _strict_int(seed, 0, 2**32 - 1):
        raise ValueError('invalid seed')
    parts: dict[str, list[int]] = {'train': [], 'validation': [], 'test': []}
    for label in (0, 1):
        ids = [i for i, row in enumerate(rows) if row.label == label]
        random.Random(seed + label).shuffle(ids)
        a = int(len(ids) * 0.6)
        b = int(len(ids) * 0.8)
        parts['train'].extend(ids[:a]); parts['validation'].extend(ids[a:b]); parts['test'].extend(ids[b:])
    for key in parts:
        parts[key].sort()
    assert len(set(sum((parts[k] for k in parts), []))) == len(rows)
    return {k: tuple(v) for k, v in parts.items()}


def fit_standardizer(rows: tuple[Row, ...], train: tuple[int, ...]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not train or len(set(train)) != len(train) or any(type(i) is not int or i < 0 or i >= len(rows) for i in train):
        raise ValueError('invalid train indices')
    means = tuple(sum(rows[i].features[j] for i in train) / len(train) for j in range(_FEATURES))
    sd = tuple(max((sum((rows[i].features[j] - means[j]) ** 2 for i in train) / len(train)) ** 0.5, 1e-9) for j in range(_FEATURES))
    if not all(_finite_number(x) for x in means + sd):
        raise ValueError('non-finite standardization')
    return means, sd


def _features(row: Row, mu: tuple[float, ...], sigma: tuple[float, ...]) -> tuple[float, ...]:
    return (1.0,) + tuple((x - mu[j]) / sigma[j] for j, x in enumerate(row.features))


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _loss(z: float, y: int) -> float:
    return max(z, 0.0) - y * z + math.log1p(math.exp(-abs(z)))


def _metrics(rows: tuple[Row, ...], ids: tuple[int, ...], weights: tuple[float, ...], mu: tuple[float, ...], sd: tuple[float, ...]) -> dict[str, float | int]:
    if not ids:
        raise ValueError('empty evaluation set')
    correct = 0; total_loss = 0.0; tp = 0; fp = 0; fn = 0
    for i in ids:
        row = rows[i]
        z = sum(w * v for w, v in zip(weights, _features(row, mu, sd)))
        prediction = int(_sigmoid(z) >= 0.5)
        correct += int(prediction == row.label)
        tp += int(prediction == 1 and row.label == 1)
        fp += int(prediction == 1 and row.label == 0)
        fn += int(prediction == 0 and row.label == 1)
        total_loss += _loss(z, row.label)
    return {'samples': len(ids), 'accuracy': correct / len(ids), 'loss': total_loss / len(ids),
            'precision': tp / (tp + fp) if tp + fp else 0.0,
            'recall': tp / (tp + fn) if tp + fn else 0.0}


def _checkpoint(payload: dict) -> dict:
    return {**payload, 'sha256': _digest(payload)}


def _validate_checkpoint(checkpoint: dict, dataset_hash: str, config_hash: str, epochs: int, patience: int) -> dict:
    if not isinstance(checkpoint, dict):
        raise ValueError('invalid checkpoint')
    keys = {'version', 'dataset_sha256', 'config_sha256', 'next_epoch', 'weights', 'best_weights',
            'best_epoch', 'best_validation_loss', 'bad_epochs', 'finished', 'sha256'}
    if set(checkpoint) != keys or checkpoint.get('version') != _VERSION:
        raise ValueError('invalid checkpoint fields')
    if checkpoint['dataset_sha256'] != dataset_hash or checkpoint['config_sha256'] != config_hash:
        raise ValueError('checkpoint source/config mismatch')
    n = checkpoint['next_epoch']
    if not _strict_int(n, 0, epochs) or not _strict_int(checkpoint['bad_epochs'], 0, epochs) or type(checkpoint['finished']) is not bool:
        raise ValueError('invalid checkpoint progress')
    if checkpoint['finished'] and n == 0:
        raise ValueError('invalid completed state')
    for key in ('weights', 'best_weights'):
        value = checkpoint[key]
        if not isinstance(value, list) or len(value) != _FEATURES + 1 or not all(_finite_number(x, 1e8) for x in value):
            raise ValueError('invalid checkpoint weights')
    best = checkpoint['best_epoch']
    val = checkpoint['best_validation_loss']
    if not (_strict_int(best, -1, max(n-1, 0)) and (best == -1 if n == 0 else best >= 0)):
        raise ValueError('invalid best epoch')
    if (val is None) != (n == 0) or (val is not None and (not _finite_number(val) or val < 0)):
        raise ValueError('invalid validation loss')
    if checkpoint['bad_epochs'] != (0 if n == 0 else n - 1 - best):
        raise ValueError('invalid early stopping counter')
    if checkpoint['finished'] != (n == epochs or checkpoint['bad_epochs'] >= patience):
        raise ValueError('invalid completion flag')
    if type(checkpoint['sha256']) is not str or _digest({k: v for k, v in checkpoint.items() if k != 'sha256'}) != checkpoint['sha256']:
        raise ValueError('checkpoint checksum mismatch')
    return json.loads(json.dumps(checkpoint, allow_nan=False))


def train(rows: tuple[Row, ...], config: Config = Config(), checkpoint: dict | None = None,
          stop_after_epoch: int | None = None) -> dict:
    """Train from scratch or resume *after* a completed epoch with no replay.

    Checksum detects accidental corruption only; it cannot authenticate the
    caller or provide durable/atomic persistence or exactly-once outside effects.
    """
    validate_rows(rows)
    if not isinstance(config, Config):
        raise ValueError('invalid config')
    if stop_after_epoch is not None and not _strict_int(stop_after_epoch, 0, config.epochs):
        raise ValueError('invalid stop epoch')
    dataset_hash = _digest({'generation': 'synthetic-v1', 'rows': rows})
    config_hash = _digest(config.__dict__)
    ids = split_indices(rows, config.seed)
    mu, sigma = fit_standardizer(rows, ids['train'])
    if checkpoint is None:
        state = _checkpoint({'version': _VERSION, 'dataset_sha256': dataset_hash, 'config_sha256': config_hash,
                            'next_epoch': 0, 'weights': [0.0] * (_FEATURES + 1), 'best_weights': [0.0] * (_FEATURES + 1),
                            'best_epoch': -1, 'best_validation_loss': None, 'bad_epochs': 0, 'finished': False})
    else:
        state = _validate_checkpoint(checkpoint, dataset_hash, config_hash, config.epochs, config.patience)
    limit = min(config.epochs, stop_after_epoch if stop_after_epoch is not None else config.epochs)
    for epoch in range(state['next_epoch'], limit):
        if state['finished']:
            break
        weights = list(state['weights'])
        order = list(ids['train'])
        random.Random(config.seed ^ (epoch * 0x9E3779B1)).shuffle(order)
        for start in range(0, len(order), config.batch_size):
            batch = order[start:start + config.batch_size]
            grad = [0.0] * len(weights)
            for i in batch:
                x = _features(rows[i], mu, sigma)
                z = sum(w * v for w, v in zip(weights, x))
                error = _sigmoid(z) - rows[i].label
                for j in range(len(grad)):
                    grad[j] += error * x[j] / len(batch)
            for j in range(1, len(grad)):
                grad[j] += config.l2 * weights[j]
            norm = math.sqrt(sum(g * g for g in grad))
            scale = min(1.0, config.gradient_clip / norm) if norm else 1.0
            weights = [w - config.learning_rate * g * scale for w, g in zip(weights, grad)]
            if not all(_finite_number(w, 1e8) for w in weights):
                raise ValueError('nonfinite optimizer state')
        val_loss = _metrics(rows, ids['validation'], tuple(weights), mu, sigma)['loss']
        improved = state['best_validation_loss'] is None or val_loss < state['best_validation_loss'] - 1e-10
        bad = 0 if improved else state['bad_epochs'] + 1
        state = _checkpoint({'version': _VERSION, 'dataset_sha256': dataset_hash, 'config_sha256': config_hash,
                             'next_epoch': epoch + 1, 'weights': weights,
                             'best_weights': list(weights if improved else state['best_weights']),
                             'best_epoch': epoch if improved else state['best_epoch'],
                             'best_validation_loss': val_loss if improved else state['best_validation_loss'],
                             'bad_epochs': bad, 'finished': bad >= config.patience or epoch + 1 >= config.epochs})
    return state


def report(rows: tuple[Row, ...], config: Config, checkpoint: dict) -> dict:
    """Evaluate final selected model on the held-out test only after training."""
    validate_rows(rows)
    if not isinstance(config, Config):
        raise ValueError('invalid config')
    state = _validate_checkpoint(checkpoint, _digest({'generation': 'synthetic-v1', 'rows': rows}), _digest(config.__dict__), config.epochs, config.patience)
    if not state['finished']:
        raise ValueError('training is not complete')
    ids = split_indices(rows, config.seed)
    mu, sd = fit_standardizer(rows, ids['train'])
    weights = tuple(state['best_weights'])
    majority = max(sum(rows[i].label == label for i in ids['train']) for label in (0, 1))
    baseline_label = 0 if sum(rows[i].label == 0 for i in ids['train']) >= majority else 1
    test = _metrics(rows, ids['test'], weights, mu, sd)
    test_baseline = sum(rows[i].label == baseline_label for i in ids['test']) / len(ids['test'])
    return {'scope': 'synthetic_binary_classification_only', 'training_type': 'real_cpu_optimizer',
            'dataset_sha256': state['dataset_sha256'], 'config_sha256': state['config_sha256'],
            'checkpoint_sha256': state['sha256'], 'epochs_completed': state['next_epoch'],
            'best_validation_epoch': state['best_epoch'], 'samples': {k: len(v) for k, v in ids.items()},
            'train': _metrics(rows, ids['train'], weights, mu, sd),
            'validation': _metrics(rows, ids['validation'], weights, mu, sd),
            'test': test, 'test_majority_baseline_accuracy': test_baseline,
            'limitations': 'No user data, pretrained models, GPU, distributed training, model registry or production serving.'}
