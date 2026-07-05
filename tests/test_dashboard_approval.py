import unittest

from app.ui.dashboard import app, reset_approval_state


class DashboardApprovalTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        reset_approval_state()

    def test_approve_route_updates_state_and_message(self):
        response = self.client.post("/approve")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Approved Successfully", response.get_data(as_text=True))
        self.assertIn("Approved", response.get_data(as_text=True))
        self.assertIn("Waiting to Send", response.get_data(as_text=True))

    def test_reject_route_updates_state_and_message(self):
        response = self.client.post("/reject")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Rejected Successfully", response.get_data(as_text=True))
        self.assertIn("Rejected by Engineer", response.get_data(as_text=True))
        self.assertIn("Email will not be sent", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
