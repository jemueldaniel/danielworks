import unittest,json
from pathlib import Path
from retrieval import *
class T(unittest.TestCase):
 def setUp(self): self.data=json.loads(Path('dataset.v1.json').read_text())
 def test_baseline_is_reproducible(self):
  a=evaluate(self.data); b=evaluate(self.data); self.assertEqual(a,b); self.assertEqual(a['mrr'],1.0); self.assertEqual(a['failures'],[])
 def test_failure_analysis_is_inspectable(self):
  x=json.loads(json.dumps(self.data)); x['queries'][0]['query']='cancellation task'; r=evaluate(x); self.assertEqual(len(r['failures']),1); self.assertEqual(r['failures'][0]['query_id'],'q1')
 def test_input_and_k_bounds(self):
  with self.assertRaisesRegex(ValueError,'invalid_doc'): index([{'id':'x','text':'y','extra':1}])
  with self.assertRaisesRegex(ValueError,'invalid_k'): retrieve(index(self.data['documents']),'x',99)
if __name__=='__main__': unittest.main()
