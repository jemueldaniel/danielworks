import unittest
from simulator import *
class T(unittest.TestCase):
 def test_transfer_and_payer_scoped_replay_protection(self):
  l=Ledger(); l.mint('a',10); l.mint('b',10); l.transfer(payer='a',payee='c',amount=3,intent_id='i1')
  with self.assertRaisesRegex(TxError,'replay'): l.transfer(payer='a',payee='c',amount=1,intent_id='i1')
  l.transfer(payer='b',payee='c',amount=1,intent_id='i1'); self.assertEqual(l.bal['c'],4)
 def test_failed_transfer_does_not_consume_intent(self):
  l=Ledger(); l.mint('a',1)
  with self.assertRaisesRegex(TxError,'insufficient_funds'): l.transfer(payer='a',payee='b',amount=2,intent_id='i')
  l.mint('a',1); l.transfer(payer='a',payee='b',amount=2,intent_id='i'); self.assertEqual(l.bal['b'],2)
 def test_rejects_self_and_nonpositive(self):
  l=Ledger(); l.mint('a',5)
  for amount,payee in [(0,'b'),(1,'a')]:
   with self.assertRaises(TxError): l.transfer(payer='a',payee=payee,amount=amount,intent_id='x')
if __name__=='__main__': unittest.main()
