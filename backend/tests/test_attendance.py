from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.utils import timezone

from accounts.models import Role
from attendance.models import Attendance, EventQR, VolunteerHours
from attendance.services import calculate_hours
from certificates.models import Certificate
from events.models import ApplicationStatus, EventApplication, EventStatus
from notifications.models import Notification

from .base import BaseAPITest


class AttendanceTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        # Live event: started 30 min ago, ends in 2.5 hours
        self.event = self.make_event(starts_in=-timedelta(minutes=30), duration=timedelta(hours=3))
        self.app = EventApplication.objects.create(volunteer=self.volunteer, event=self.event, email="vol@test.in", status=ApplicationStatus.APPROVED)

    def qr(self):
        self.auth(self.organizer)
        res = self.client.post(f"/api/events/{self.event.id}/qr/")
        self.assertEqual(res.status_code, 201, res.data)
        return res.data

    def test_qr_generation(self):
        data = self.qr()
        self.assertTrue(data["qr_image"].startswith("data:image/png;base64,"))
        self.assertEqual(data["check_in_url"], f"https://nss.example.test/attendance/check-in/{data['token']}")
        self.assertGreaterEqual(len(data["token"]), 40)
        self.assertNotIn("vol@test.in", data["check_in_url"])
        again = self.qr()
        self.assertFalse(EventQR.objects.get(token=data["token"]).active)  # rotated
        self.assertTrue(EventQR.objects.get(token=again["token"]).active)

    def test_qr_only_by_organizer_and_for_approved_events(self):
        self.auth(self.volunteer)
        self.assertEqual(self.client.post(f"/api/events/{self.event.id}/qr/").status_code, 403)
        pending = self.make_event(status=EventStatus.PENDING)
        self.auth(self.organizer)
        self.assertEqual(self.client.post(f"/api/events/{pending.id}/qr/").status_code, 400)

    def test_check_in_validation(self):
        token = self.qr()["token"]
        self.auth(self.volunteer)
        self.assertEqual(self.client.post("/api/attendance/check-in/", {"token": "nope"}).data["code"], "token_invalid")
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post("/api/attendance/check-in/", {"token": token}).status_code, 401)
        # not registered
        stranger = self.make_user("s@test.in", Role.VOLUNTEER)
        self.auth(stranger)
        self.assertEqual(self.client.post("/api/attendance/check-in/", {"token": token}).data["code"], "not_registered")
        # registered but not approved
        EventApplication.objects.create(volunteer=stranger, event=self.event, email="s@test.in", status=ApplicationStatus.PENDING)
        self.assertEqual(self.client.post("/api/attendance/check-in/", {"token": token}).data["code"], "not_approved")
        # valid
        self.auth(self.volunteer)
        res = self.client.post("/api/attendance/check-in/", {"token": token})
        self.assertEqual(res.status_code, 201, res.data)
        att = Attendance.objects.get(volunteer=self.volunteer, event=self.event)
        self.assertEqual(att.status, "LATE")  # 30 min after start > 15 min grace
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, EventStatus.ONGOING)
        self.assertTrue(Notification.objects.filter(recipient=self.volunteer, notification_type="ATTENDANCE_CONFIRMED").exists())

    def test_duplicate_check_in(self):
        token = self.qr()["token"]
        self.auth(self.volunteer)
        self.client.post("/api/attendance/check-in/", {"token": token})
        res = self.client.post("/api/attendance/check-in/", {"token": token})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "already_checked_in")
        self.assertEqual(Attendance.objects.filter(volunteer=self.volunteer, event=self.event).count(), 1)

    def test_check_in_time_window(self):
        future = self.make_event(starts_in=timedelta(days=2))
        EventApplication.objects.create(volunteer=self.volunteer, event=future, email="v@test.in", status=ApplicationStatus.APPROVED)
        self.auth(self.organizer)
        token = self.client.post(f"/api/events/{future.id}/qr/").data["token"]
        self.auth(self.volunteer)
        self.assertEqual(self.client.post("/api/attendance/check-in/", {"token": token}).data["code"], "too_early")

    def test_expired_and_inactive_tokens(self):
        token = self.qr()["token"]
        EventQR.objects.filter(token=token).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.auth(self.volunteer)
        self.assertEqual(self.client.post("/api/attendance/check-in/", {"token": token}).data["code"], "token_expired")

    def test_checkout_calculates_hours(self):
        token = self.qr()["token"]
        self.auth(self.volunteer)
        t0 = timezone.now()
        self.client.post("/api/attendance/check-in/", {"token": token})
        with mock.patch("django.utils.timezone.now", return_value=t0 + timedelta(hours=2, minutes=15)):
            res = self.client.post("/api/attendance/check-out/", {"token": token})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertAlmostEqual(res.data["hours"], 2.25, places=1)
        rec = VolunteerHours.objects.get(volunteer=self.volunteer, event=self.event)
        self.assertEqual(rec.category, "ABP1")
        self.assertFalse(rec.verified)
        self.assertEqual(self.client.post("/api/attendance/check-out/", {"token": token}).data["code"], "already_checked_out")

    def test_checkout_too_soon_after_checkin(self):
        token = self.qr()["token"]
        self.auth(self.volunteer)
        self.client.post("/api/attendance/check-in/", {"token": token})
        self.assertEqual(self.client.post("/api/attendance/check-out/", {"token": token}).data["code"], "too_soon")

    def test_checkout_without_checkin(self):
        token = self.qr()["token"]
        self.auth(self.volunteer)
        self.assertEqual(self.client.post("/api/attendance/check-out/", {"token": token}).data["code"], "not_checked_in")

    def test_hours_calculation_is_capped(self):
        start = timezone.now()
        self.assertEqual(calculate_hours(start, start + timedelta(minutes=90), self.event), Decimal("1.50"))
        # 3h event + 60 min early window = 4h cap
        self.assertEqual(calculate_hours(start, start + timedelta(hours=10), self.event), Decimal("4.00"))
        self.assertEqual(calculate_hours(start, start - timedelta(minutes=5), self.event), Decimal("0.00"))

    def test_feedback_required_before_certificate(self):
        token = self.qr()["token"]
        self.auth(self.volunteer)
        # feedback before attending is refused
        self.assertEqual(self.client.post(f"/api/events/{self.event.id}/feedback/", {"rating": 5}).data["code"], "not_attended")
        t0 = timezone.now()
        self.client.post("/api/attendance/check-in/", {"token": token})
        self.assertEqual(self.client.post(f"/api/events/{self.event.id}/feedback/", {"rating": 5}).data["code"], "not_checked_out")
        with mock.patch("django.utils.timezone.now", return_value=t0 + timedelta(hours=2)):
            self.client.post("/api/attendance/check-out/", {"token": token})
        self.assertFalse(Certificate.objects.filter(volunteer=self.volunteer).exists())
        self.assertEqual(self.client.post(f"/api/events/{self.event.id}/feedback/", {"rating": 9}).status_code, 400)
        res = self.client.post(f"/api/events/{self.event.id}/feedback/", {"rating": 5, "comments": "Great"})
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(VolunteerHours.objects.get(volunteer=self.volunteer, event=self.event).verified)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, ApplicationStatus.COMPLETED)
        cert = Certificate.objects.get(volunteer=self.volunteer, event=self.event)
        self.assertEqual(res.data["certificate_id"], cert.certificate_id)
        self.assertTrue(cert.pdf_file.name.endswith(".pdf"))
        with cert.pdf_file.open("rb") as f:
            self.assertTrue(f.read(5).startswith(b"%PDF-"))
        self.assertEqual(cert.verify_url, f"https://nss.example.test/certificate/{cert.certificate_id}/verify")
        self.assertEqual(self.client.post(f"/api/events/{self.event.id}/feedback/", {"rating": 4}).data["code"], "feedback_exists")

    def test_complete_event_closes_out(self):
        token = self.qr()["token"]
        v2 = self.make_user("v2@test.in", Role.VOLUNTEER)
        EventApplication.objects.create(volunteer=v2, event=self.event, email="v2@test.in", status=ApplicationStatus.APPROVED)
        self.auth(self.volunteer)
        self.client.post("/api/attendance/check-in/", {"token": token})
        self.auth(self.organizer)
        res = self.client.post(f"/api/events/{self.event.id}/set-status/", {"status": "COMPLETED"})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["close_out"], {"auto_checked_out": 1, "marked_absent": 1})
        self.assertEqual(Attendance.objects.get(volunteer=v2, event=self.event).status, "ABSENT")
        self.assertTrue(res.data["summary"])
        self.assertFalse(EventQR.objects.filter(event=self.event, active=True).exists())


class CertificateVerificationTests(BaseAPITest):
    def test_public_verification(self):
        event = self.make_event(starts_in=-timedelta(days=2))
        from certificates.services import generate_certificate

        cert, _ = generate_certificate(self.volunteer, event, Decimal("3.00"))
        self.client.force_authenticate(None)
        res = self.client.get(f"/api/certificates/{cert.certificate_id}/verify/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["valid"])
        self.assertEqual(res.data["event"], event.title)
        self.assertEqual(res.data["hours"], 3.0)
        self.assertEqual(res.data["organizer"], self.ngo.name)
        self.assertNotIn("email", res.data)  # no private info
        self.assertNotIn("phone", res.data)
        bad = self.client.get("/api/certificates/NSSC-0000-DEADBEEF/verify/")
        self.assertEqual(bad.status_code, 404)
        self.assertFalse(bad.data["valid"])

    def test_certificate_download_permissions(self):
        event = self.make_event(starts_in=-timedelta(days=2))
        from certificates.services import generate_certificate

        cert, _ = generate_certificate(self.volunteer, event, Decimal("2.00"))
        other = self.make_user("o@test.in", Role.VOLUNTEER)
        self.auth(other)
        self.assertEqual(self.client.get(f"/api/certificates/{cert.id}/download/").status_code, 403)
        self.auth(self.volunteer)
        res = self.client.get(f"/api/certificates/{cert.id}/download/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertEqual(self.client.get("/api/certificates/").data["count"], 1)
