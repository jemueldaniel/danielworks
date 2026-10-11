# Offline transaction semantics simulator

Synthetic accounts exercise payer-scoped replay protection, atomic balance updates and failure rollback. It mirrors broadly applicable smart-contract transaction invariants without copying company contracts.

Run: `python -m unittest -v test_simulator.py`.

Limit: this is a **simulation**, not compiled Solidity/EVM execution. Solidity source exists in private evidence, but no compiler/tool install was admitted for this batch.
