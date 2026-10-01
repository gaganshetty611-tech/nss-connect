from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import Role
from events.models import Event, EventStatus
from ngos.models import NGO
from notifications.models import Notification
from nss_units.models import College, NSSUnit, VerificationStatus

from .base import BaseAPITest

EVENT = {
    "title": "Tree Plantation Drive", "description": "Planting saplings in the park", "category": "ABP1",
    "date": "2099-01-10", "start_time": "08:00", "end_time": "11:00", "location": "Aarey",
    "maximum_volunteers": 10, "contact_email": "org@test.in", "required_skills": ["Tree Plantation"],
}


class PermissionTests(BaseAPITest):
    def test_volunteer_cannot_create_event(self):
        self.auth(self.volunteer)
        self.assertEqual(self.client.post("/api/events/", EVENT, format="json").status_code, 403)

    def test_anonymous_cannot_create_event(self):
        self.assertEqual(self.client.post("/api/events/", EVENT, format="json").status_code, 401)

    def test_unverified_ngo_cannot_post(self):
        other = self.make_user("org2@test.in", Role.NGO_ORGANIZER)
        NGO.objects.create(owner=other, name="Pending NGO", email="p@test.in")
        self.auth(other)
        res = self.client.post("/api/events/", EVENT, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertIn("verified", res.data["detail"])

    def test_organizer_cannot_edit_or_delete_others_event(self):
        event = self.make_event(organizer=self.coordinator, status=EventStatus.PENDING)
        self.auth(self.organizer)
        self.assertIn(self.client.patch(f"/api/events/{event.id}/", {"title": "Hacked"}, format="json").status_code, (403, 404))
        self.assertIn(self.client.delete(f"/api/events/{event.id}/").status_code, (403, 404))
        event.refresh_from_db()
        self.assertEqual(event.title, "Beach Clean-up")

    def test_pending_events_hidden_from_public(self):
        pending = self.make_event(status=EventStatus.PENDING, title="Secret pending")
        res = self.client.get("/api/events/", {"all": "true"})
        self.assertNotIn(pending.id, [e["id"] for e in res.data["results"]])
        self.assertEqual(self.client.get(f"/api/events/{pending.id}/").status_code, 404)
        self.auth(self.organizer)  # owner can see it
        self.assertEqual(self.client.get(f"/api/events/{pending.id}/").status_code, 200)

    def test_non_admin_cannot_approve_event(self):
        event = self.make_event(status=EventStatus.PENDING)
        self.auth(self.organizer)
        self.assertEqual(self.client.post(f"/api/events/{event.id}/approve/").status_code, 403)

    def test_college_admin_scope(self):
        other_college = College.objects.create(university=self.uni, name="Other College")
        other_coord = self.make_user("c2@test.in", Role.NSS_COORDINATOR)
        other_unit = NSSUnit.objects.create(college=other_college, unit_number="9", coordinator=other_coord, verification_status=VerificationStatus.VERIFIED)
        admin = self.make_user("cadmin@test.in", Role.COLLEGE_ADMIN)
        admin.profile.college = self.college
        admin.profile.save()
        mine = self.make_event(organizer=self.coordinator, status=EventStatus.PENDING, nss_unit=self.unit, college=self.college, university=self.uni)
        theirs = self.make_event(organizer=other_coord, status=EventStatus.PENDING, nss_unit=other_unit, college=other_college, university=self.uni)
        self.auth(admin)
        self.assertEqual(self.client.post(f"/api/events/{theirs.id}/approve/").status_code, 403)
        self.assertEqual(self.client.post(f"/api/events/{mine.id}/approve/").status_code, 200)
        # cannot verify units outside scope
        self.assertEqual(self.client.post(f"/api/nss-units/{other_unit.id}/verify/").status_code, 403)
        # cannot review NGOs at all (university/super only)
        self.assertEqual(self.client.post(f"/api/ngos/{self.ngo.id}/suspend/").status_code, 403)

    def test_admin_endpoints_require_admin(self):
        self.auth(self.volunteer)
        for url in ["/api/admin/users/", "/api/dashboard/admin/", "/api/reports/?type=abp1"]:
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_only_super_admin_changes_roles(self):
        uadmin = self.make_user("u@test.in", Role.UNIVERSITY_ADMIN)
        self.auth(uadmin)
        self.assertEqual(self.client.patch(f"/api/admin/users/{self.volunteer.id}/", {"role": "SUPER_ADMIN"}, format="json").status_code, 403)
        self.auth(self.super)
        self.assertEqual(self.client.patch(f"/api/admin/users/{self.volunteer.id}/", {"role": "NSS_COORDINATOR"}, format="json").status_code, 200)

    def test_notifications_are_private(self):
        n = Notification.objects.create(recipient=self.organizer, notification_type="EVENT_APPROVED", title="x", message="y")
        self.auth(self.volunteer)
        self.assertEqual(self.client.post(f"/api/notifications/{n.id}/read/").status_code, 404)
        self.assertEqual(self.client.get("/api/notifications/").data["count"], 0)

    def test_ngo_documents_private_and_validated(self):
        self.auth(self.volunteer)
        self.assertEqual(self.client.get(f"/api/ngos/{self.ngo.id}/documents/").status_code, 403)
        self.auth(self.organizer)
        bad = SimpleUploadedFile("reg.pdf", b"MZ this is an exe", content_type="application/pdf")
        self.assertEqual(self.client.post(f"/api/ngos/{self.ngo.id}/documents/", {"document_type": "PAN", "file": bad}, format="multipart").status_code, 400)
        exe = SimpleUploadedFile("reg.exe", b"%PDF-1.4 fake", content_type="application/pdf")
        self.assertEqual(self.client.post(f"/api/ngos/{self.ngo.id}/documents/", {"document_type": "PAN", "file": exe}, format="multipart").status_code, 400)
        good = SimpleUploadedFile("reg.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf")
        res = self.client.post(f"/api/ngos/{self.ngo.id}/documents/", {"document_type": "PAN", "file": good}, format="multipart")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertNotIn("file", res.data)
        # public media URL for private docs is blocked
        from ngos.models import VerificationDocument

        doc = VerificationDocument.objects.get(pk=res.data["id"])
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f"/media/{doc.file.name}").status_code, 404)
        self.auth(self.super)
        self.assertEqual(self.client.get(f"/api/documents/{doc.id}/download/").status_code, 200)

    def test_ngo_verification_workflow(self):
        other = self.make_user("org3@test.in", Role.NGO_ORGANIZER)
        self.auth(other)
        res = self.client.post("/api/ngos/", {"name": "Akshar", "email": "a@test.in", "focus_areas": ["EDUCATION"]}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        ngo_id = res.data["id"]
        self.client.force_authenticate(None)
        self.assertNotIn(ngo_id, [n["id"] for n in self.client.get("/api/ngos/").data["results"]])
        self.auth(self.super)
        self.assertEqual(self.client.post(f"/api/ngos/{ngo_id}/verify/").status_code, 200)
        self.client.force_authenticate(None)
        listed = {n["id"]: n for n in self.client.get("/api/ngos/").data["results"]}
        self.assertTrue(listed[ngo_id]["verified"])
        self.assertTrue(Notification.objects.filter(recipient=other, notification_type="NGO_VERIFIED").exists())
