import unittest
from catalog import CATEGORIES,LEVELS,validate,build,summary,export,examples

class CatalogTests(unittest.TestCase):
 def setUp(self):
  self.row={"technology":"Python","category":"Backend","level":"public-tested","public_reference":"examples/retrieval_lab/retrieval.py"}
 def test_valid(self): self.assertTrue(validate(self.row))
 def test_summary(self):
  self.assertEqual(summary([self.row])["public-tested"],1)
 def test_all_defaults_unverified(self):
  items=examples()
  self.assertEqual(len(items),sum(map(len,CATEGORIES.values())))
  self.assertTrue(all(x["level"]=="unverified" for x in items))
 def test_export(self):
  import json
  self.assertEqual(json.loads(export([self.row]))["entries"][0],self.row)
 def test_no_private_links(self):
  for level in LEVELS-{"public-tested"}:
   with self.subTest(level=level):
    with self.assertRaises(ValueError): build([{**self.row,"level":level}])
 def test_duplicates(self):
  with self.assertRaises(ValueError):build([self.row,self.row])
 def test_size(self):
  with self.assertRaises(ValueError):build([self.row]*101)
 def test_malformed(self):
  for row in (None,{},{"technology":"Python"},[],42):
   with self.subTest(row=row):self.assertFalse(validate(row))
 def test_traversal(self):
  for ref in ("examples/../private.txt","D:/secrets","https://private.example","examples/a b"):
   with self.subTest(ref=ref):
    self.assertFalse(validate({**self.row,"public_reference":ref}))
 def test_no_unknown_tech(self):
  self.assertFalse(validate({**self.row,"technology":"InventedCloud"}))
 def test_does_not_mutate(self):
  before=self.row.copy();build([self.row]);self.assertEqual(self.row,before)

if __name__=="__main__":unittest.main()
