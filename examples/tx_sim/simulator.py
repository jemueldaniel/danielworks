class TxError(Exception): pass
class Ledger:
    def __init__(self): self.bal={}; self.used=set()
    def mint(self,acct,amount): self.bal[acct]=self.bal.get(acct,0)+amount
    def transfer(self,*,payer,payee,amount,intent_id):
        if not intent_id or amount<=0 or not payer or not payee or payer==payee: raise TxError('invalid_intent')
        key=(payer,intent_id)
        if key in self.used: raise TxError('replay')
        if self.bal.get(payer,0)<amount: raise TxError('insufficient_funds')
        before=dict(self.bal)
        try:
            self.used.add(key); self.bal[payer]-=amount; self.bal[payee]=self.bal.get(payee,0)+amount
            return {'payer':payer,'payee':payee,'amount':amount,'intent_id':intent_id}
        except Exception:
            self.bal=before; self.used.discard(key); raise
