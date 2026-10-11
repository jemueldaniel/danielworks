import unittest
from service import ItemService, InProcessSdk, ApiError

class ApiSdkTests(unittest.TestCase):
    def setUp(self): self.s=ItemService()
    def test_idempotent_create_replays_same_result(self):
        a=self.s.create(owner_id="a",idempotency_key="k1",payload={"name":"alpha"})
        b=self.s.create(owner_id="a",idempotency_key="k1",payload={"name":"alpha"})
        self.assertEqual(a["item"],b["item"]); self.assertEqual(b["status"],"replayed")
    def test_idempotency_conflict_is_scoped_and_rejected(self):
        self.s.create(owner_id="a",idempotency_key="k1",payload={"name":"alpha"})
        with self.assertRaisesRegex(ApiError,"idempotency_conflict"):
            self.s.create(owner_id="a",idempotency_key="k1",payload={"name":"beta"})
        self.assertEqual(self.s.create(owner_id="b",idempotency_key="k1",payload={"name":"beta"})["status"],"created")
    def test_validation_rejects_unknown_fields(self):
        with self.assertRaisesRegex(ApiError,"invalid_payload"):
            self.s.create(owner_id="a",idempotency_key="k",payload={"name":"x","admin":True})
    def test_pagination_and_tenant_isolation(self):
        a=InProcessSdk(self.s,"a"); b=InProcessSdk(self.s,"b")
        for i in range(5): a.create_item(f"a{i}",f"a{i}")
        for i in range(2): b.create_item(f"b{i}",f"b{i}")
        self.assertEqual([x["name"] for x in a.list_all(2)],[f"a{i}" for i in range(5)])
        self.assertEqual([x["name"] for x in b.list_all(1)],[f"b{i}" for i in range(2)])
    def test_limit_and_cursor_are_bounded(self):
        with self.assertRaisesRegex(ApiError,"invalid_limit"): self.s.list(owner_id="a",limit=99)
        with self.assertRaisesRegex(ApiError,"invalid_cursor"): self.s.list(owner_id="a",cursor="missing")

if __name__=="__main__": unittest.main()
