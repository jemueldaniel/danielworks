# Prior supplementary batch: retained and rechecked

The prior supplementary source and tests remain unchanged. Current results and exact command scope are consolidated in [TEST_EVIDENCE.md](TEST_EVIDENCE.md). Older counts are not silently treated as new proof.

A fresh root-directory invocation of `retrieval_lab` failed because that pre-existing test opens `dataset.v1.json` relative to its working directory. The failed log is preserved in the private review pack. Re-running the original documented command **inside `examples/retrieval_lab`** passes its three tests; the source/test was not altered to hide the failed invocation.

These exercises remain explicitly classified as lexical baseline, Python API contract exercise, in-process MCP-shaped tool simulation and Python transaction simulation. The real networked MCP/browser/database work is the new evaluation workbench, not a retroactive claim about the old exercises.
