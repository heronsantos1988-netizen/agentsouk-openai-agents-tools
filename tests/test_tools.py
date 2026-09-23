import os
import unittest

os.environ.setdefault("AGENTSOUK_API_KEY", "as_test_placeholder")

from agentsouk_openai_tools import tools


class FakeListings:
    def search(self, q, **params):
        return {"object": "list", "data": [{"id": "lst_test", "title": q}], **params}


class FakeJobs:
    def create(self, listing_id, input, units=None):
        return {"id": "job_test", "listing_id": listing_id, "input": input, "units": units}
    def get(self, job_id):
        return {"id": job_id, "status": "open"}
    def accept(self, job_id):
        return {"id": job_id, "status": "in_progress"}
    def deliver(self, job_id, output, message=None, preview=None):
        return {"id": job_id, "status": "delivered", "output": output, "preview": preview}
    def payment_required(self, job_id):
        return {"job_id": job_id, "error": {"code": "payment_required"}}
    def receipt(self, job_id):
        return {"receipt": {"job": {"id": job_id}}, "signature": {"alg": "EdDSA"}}
    def pay_gasless(self, job_id, signer):
        return {"id": job_id, "status": "completed", "signature": signer({"test": True})}


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.listings = FakeListings()
        self.jobs = FakeJobs()
    def inbox(self):
        return {"object": "inbox", "unread_total": 0}
    def close(self):
        pass


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.original = tools.AgentSouk
        tools.AgentSouk = FakeClient
    def tearDown(self):
        tools.AgentSouk = self.original
    def test_private_helpers_validate_objects(self):
        self.assertEqual(tools._loads_object('{"x":1}', "x"), {"x": 1})
        with self.assertRaises(ValueError):
            tools._loads_object("[1,2]", "x")
    def test_backend_search(self):
        out = tools._run(lambda c: c.listings.search("web", limit=3))
        self.assertIn('"lst_test"', out)
    def test_backend_delivery(self):
        out = tools._run(lambda c: c.jobs.deliver("job_test", {"url":"https://example.com"}))
        self.assertIn('"status":"delivered"', out)

    def test_payment_requires_operator_confirmation(self):
        blocked = tools.pay_gasless("job_test", lambda _: "0x" + "11" * 65, False)
        self.assertIn("operator_confirmation_required", blocked)
        paid = tools.pay_gasless("job_test", lambda _: "0x" + "11" * 65, True)
        self.assertIn('"status":"completed"', paid)


if __name__ == "__main__":
    unittest.main()
