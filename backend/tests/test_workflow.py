"""Section 50: the complete real workflow, end to end, through the public API only."""
import re
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.utils import timezone

from .base import PASSWORD, BaseAPITest


class CompleteWorkflowTest(BaseAPITest):
    def test_complete_workflow(self):
        c = self.client
        # Organizer creates a drive that is happening now; admin approves it.
        self.login("org@test.in")
        start = timezone.localtime(timezone.now() - timedelta(minutes=5))
        end = start + timedelta(hours=3)
        res = c.post("/api/events/", {
            "title": "Mahim Beach Clean-up", "description": "Plastic waste cleanup and segregation", "category": "ABP1",
            "date": start.date().isoformat(), "start_time": start.strftime("%H:%M"), "end_time": end.strftime("%H:%M"),
            "location": "Mahim Beach", "latitude": "19.0416", "longitude": "72.8380", "maximum_volunteers": 10,
            "contact_email": "org@test.in", "required_skills": ["Waste Segregation"],
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        event_id = res.data["id"]
        self.login("super@test.in")
        self.assertEqual(c.post(f"/api/events/{event_id}/approve/").status_code, 200)
        analytics_before = c.get("/api/analytics/").data["summary"]

        # 1. Register → 2. Email verification → 3. Login
        c.credentials()
        res = c.post("/api/auth/register/", {"email": "riya@test.in", "password": PASSWORD, "first_name": "Riya", "last_name": "Shah",
                                              "role": "VOLUNTEER", "gender": "FEMALE", "nss_unit": self.unit.id}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(self.login("riya@test.in").status_code, 403)
        uid, token = re.search(r"uid=([^&]+)&token=(\S+)", mail.outbox[-1].body).groups()
        self.assertEqual(c.post("/api/auth/verify-email/", {"uid": uid, "token": token}).status_code, 200)
        self.assertEqual(self.login("riya@test.in").status_code, 200)

        # 4. Dashboard → 5. Browse → 6. Open event → 7. Register
        dash = c.get("/api/dashboard/volunteer/").data["stats"]
        self.assertEqual((dash["events_participated"], dash["volunteer_hours"], dash["certificates"]), (0, 0.0, 0))
        listing = c.get("/api/events/", {"category": "ABP1", "search": "Mahim"}).data
        self.assertEqual([e["id"] for e in listing["results"]], [event_id])
        detail = c.get(f"/api/events/{event_id}/").data
        self.assertIsNone(detail["my_application"])
        app = c.post(f"/api/events/{event_id}/register/", {"phone": "+91 9000000000"}, format="json").data
        self.assertEqual(app["status"], "PENDING")

        # 8. Organizer sees application → 9. approves → 10. volunteer notified
        self.login("org@test.in")
        apps = c.get(f"/api/events/{event_id}/applications/").data["results"]
        self.assertEqual([a["volunteer_name"] for a in apps], ["Riya Shah"])
        self.assertEqual(c.post(f"/api/applications/{apps[0]['id']}/approve/").data["status"], "APPROVED")
        # 11. Event QR generated
        qr = c.post(f"/api/events/{event_id}/qr/").data
        qr_token = qr["check_in_url"].rsplit("/", 1)[-1]

        self.login("riya@test.in")
        notes = c.get("/api/notifications/").data
        self.assertIn("APPLICATION_APPROVED", [n["notification_type"] for n in notes["results"]])
        self.assertGreater(notes["unread_count"], 0)

        # 12. Scan QR → 13. backend validates → 14. attendance stored
        status_ = c.get("/api/attendance/scan-status/", {"token": qr_token}).data
        self.assertEqual(status_["next_action"], "check_in")
        res = c.post("/api/attendance/check-in/", {"token": qr_token})
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["attendance"]["status"], "PRESENT")

        # 15. Check out → 16. hours calculated
        t0 = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=t0 + timedelta(hours=2, minutes=30)):
            out = c.post("/api/attendance/check-out/", {"token": qr_token})
        self.assertEqual(out.status_code, 200, out.data)
        self.assertAlmostEqual(out.data["hours"], 2.5, delta=0.1)
        self.assertEqual(c.get("/api/dashboard/volunteer/").data["stats"]["pending_hours"], out.data["hours"])

        # 17. Feedback → 18. participation verified → 19. certificate generated
        fb = c.post(f"/api/events/{event_id}/feedback/", {"rating": 5, "comments": "Loved it"})
        self.assertEqual(fb.status_code, 201, fb.data)
        cert_id = fb.data["certificate_id"]
        self.assertTrue(cert_id)

        # 20. Certificate appears in dashboard
        dash = c.get("/api/dashboard/volunteer/").data
        self.assertEqual(dash["stats"]["certificates"], 1)
        self.assertEqual(dash["stats"]["events_participated"], 1)
        self.assertEqual(dash["stats"]["volunteer_hours"], out.data["hours"])
        self.assertEqual(dash["recent_certificates"][0]["certificate_id"], cert_id)
        cert = c.get("/api/certificates/").data["results"][0]
        pdf = c.get(cert["download_url"])
        self.assertEqual(pdf.status_code, 200)

        # 21. Certificate QR verification works (public)
        c.credentials()
        c.force_authenticate(None)
        self.assertTrue(cert["verify_url"].endswith(f"/certificate/{cert_id}/verify"))
        ver = c.get(f"/api/certificates/{cert_id}/verify/").data
        self.assertTrue(ver["valid"])
        self.assertEqual(ver["volunteer_name"], "Riya Shah")

        # 22. Analytics update automatically
        after = c.get("/api/analytics/").data["summary"]
        self.assertEqual(after["volunteer_hours"], round(analytics_before["volunteer_hours"] + out.data["hours"], 2))
        self.assertEqual(after["total_volunteers"], analytics_before["total_volunteers"] + 1)
        self.assertEqual(after["certificates_issued"], analytics_before["certificates_issued"] + 1)
        self.assertEqual(after["hours_by_category"]["ABP1"], out.data["hours"])
