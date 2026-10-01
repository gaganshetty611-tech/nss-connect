from datetime import timedelta

from django.db import IntegrityError, transaction

from accounts.models import Role
from events.models import ApplicationStatus, Event, EventApplication, EventStatus
from notifications.models import Notification

from .test_permissions import EVENT
from .base import BaseAPITest


class EventCrudTests(BaseAPITest):
    def test_create_event_is_pending_with_ai_theme_and_skills(self):
        self.auth(self.organizer)
        res = self.client.post("/api/events/", EVENT, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        event = Event.objects.get(pk=res.data["id"])
        self.assertEqual(event.status, EventStatus.PENDING)
        self.assertEqual(event.ngo, self.ngo)
        self.assertEqual(event.theme, "ENVIRONMENT")  # rule-based categorisation from "Planting saplings"
        self.assertEqual(list(event.required_skills.values_list("name", flat=True)), ["Tree Plantation"])

    def test_create_validation(self):
        self.auth(self.organizer)
        self.assertEqual(self.client.post("/api/events/", {**EVENT, "category": "FUN"}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/events/", {**EVENT, "date": "2000-01-01"}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/events/", {**EVENT, "end_time": "08:00"}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/events/", {**EVENT, "latitude": "123"}, format="json").status_code, 400)

    def test_update_and_delete_own_pending_event(self):
        event = self.make_event(status=EventStatus.PENDING)
        self.auth(self.organizer)
        res = self.client.patch(f"/api/events/{event.id}/", {"title": "Updated title", "maximum_volunteers": 20}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["title"], "Updated title")
        res = self.client.put(f"/api/events/{event.id}/", {**EVENT, "title": "Put title"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(self.client.delete(f"/api/events/{event.id}/").status_code, 204)
        self.assertFalse(Event.objects.filter(pk=event.id).exists())

    def test_material_edit_of_approved_event_requires_reapproval(self):
        event = self.make_event()
        self.auth(self.organizer)
        self.client.patch(f"/api/events/{event.id}/", {"location": "Versova Beach"}, format="json")
        event.refresh_from_db()
        self.assertEqual(event.status, EventStatus.PENDING)

    def test_approved_event_cannot_be_deleted_by_organizer(self):
        event = self.make_event()
        self.auth(self.organizer)
        self.assertEqual(self.client.delete(f"/api/events/{event.id}/").status_code, 403)

    def test_event_approval_and_rejection(self):
        e1 = self.make_event(status=EventStatus.PENDING)
        e2 = self.make_event(status=EventStatus.PENDING, title="Other")
        self.auth(self.super)
        res = self.client.post(f"/api/events/{e1.id}/approve/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "APPROVED")
        self.assertTrue(Notification.objects.filter(recipient=self.organizer, notification_type="EVENT_APPROVED").exists())
        res = self.client.post(f"/api/events/{e2.id}/reject/", {"note": "Incomplete details"})
        self.assertEqual(res.data["status"], "REJECTED")
        self.assertTrue(Notification.objects.filter(recipient=self.organizer, notification_type="EVENT_REJECTED").exists())
        self.client.force_authenticate(None)
        ids = [e["id"] for e in self.client.get("/api/events/").data["results"]]
        self.assertIn(e1.id, ids)
        self.assertNotIn(e2.id, ids)

    def test_admin_created_event_is_auto_approved(self):
        self.auth(self.super)
        res = self.client.post("/api/events/", {**EVENT, "category": "UNIVERSITY_EVENT"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["status"], "APPROVED")


class EventFilterTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.e1 = self.make_event(title="Beach cleanup", category="ABP1", starts_in=timedelta(days=2))
        self.e2 = self.make_event(title="Blood camp", category="ABP2", description="blood donation", starts_in=timedelta(days=4), location="Dadar")
        self.e3 = self.make_event(title="College fest", category="COLLEGE_EVENT", description="Annual fest", starts_in=timedelta(days=6))
        self.e4 = self.make_event(title="Uni rally", category="UNIVERSITY_EVENT", description="Road safety rally", starts_in=timedelta(days=8), maximum_volunteers=1)
        self.e2.required_skills.set([__import__("events.models", fromlist=["EventSkill"]).EventSkill.objects.create(name="First Aid")])
        EventApplication.objects.create(volunteer=self.volunteer, event=self.e4, email="v@test.in", status=ApplicationStatus.APPROVED)

    def ids(self, **params):
        res = self.client.get("/api/events/", params)
        self.assertEqual(res.status_code, 200)
        return {e["id"] for e in res.data["results"]}

    def test_category_filter_is_server_side(self):
        self.assertEqual(self.ids(category="ABP1"), {self.e1.id})
        self.assertEqual(self.ids(category="ABP2"), {self.e2.id})
        self.assertEqual(self.ids(category="COLLEGE_EVENT"), {self.e3.id})
        self.assertEqual(self.ids(category="UNIVERSITY_EVENT"), {self.e4.id})
        self.assertEqual(len(self.ids(category="ALL")), 4)

    def test_search_date_location_skill_availability(self):
        self.assertEqual(self.ids(search="cleanup"), {self.e1.id})
        self.assertEqual(self.ids(date=self.e2.date.isoformat()) & {self.e2.id}, {self.e2.id})
        self.assertEqual(self.ids(location="dadar"), {self.e2.id})
        self.assertEqual(self.ids(skill="first aid"), {self.e2.id})
        self.assertNotIn(self.e4.id, self.ids(available="true"))

    def test_pagination(self):
        res = self.client.get("/api/events/", {"page_size": 2})
        self.assertEqual(res.data["count"], 4)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIsNotNone(res.data["next"])


class RegistrationWorkflowTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.event = self.make_event(maximum_volunteers=1)

    def test_register_creates_application_and_notifies(self):
        self.auth(self.volunteer)
        res = self.client.post(f"/api/events/{self.event.id}/register/", {"phone": "+91 9876543210", "skills": ["Teaching"]}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        app = EventApplication.objects.get(event=self.event, volunteer=self.volunteer)
        self.assertEqual(app.status, ApplicationStatus.PENDING)
        self.assertEqual(app.nss_unit, self.unit)
        self.assertEqual(app.college, self.college)
        self.assertTrue(Notification.objects.filter(recipient=self.organizer, notification_type="APPLICATION_CREATED").exists())

    def test_duplicate_registration_prevented(self):
        self.auth(self.volunteer)
        self.client.post(f"/api/events/{self.event.id}/register/", {}, format="json")
        res = self.client.post(f"/api/events/{self.event.id}/register/", {}, format="json")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(EventApplication.objects.filter(event=self.event, volunteer=self.volunteer).count(), 1)
        # enforced by the database, not just the view
        with self.assertRaises(IntegrityError), transaction.atomic():
            EventApplication.objects.create(event=self.event, volunteer=self.volunteer, email="x@test.in")

    def test_only_volunteers_register(self):
        self.auth(self.organizer)
        self.assertEqual(self.client.post(f"/api/events/{self.event.id}/register/", {}, format="json").status_code, 403)

    def test_cannot_register_for_pending_event(self):
        pending = self.make_event(status=EventStatus.PENDING)
        self.auth(self.volunteer)
        self.assertEqual(self.client.post(f"/api/events/{pending.id}/register/", {}, format="json").status_code, 404)

    def test_cancel_updates_record_and_reregister(self):
        self.auth(self.volunteer)
        self.client.post(f"/api/events/{self.event.id}/register/", {}, format="json")
        res = self.client.post(f"/api/events/{self.event.id}/cancel/")
        self.assertEqual(res.status_code, 200)
        app = EventApplication.objects.get(event=self.event, volunteer=self.volunteer)
        self.assertEqual(app.status, ApplicationStatus.CANCELLED)
        res = self.client.post(f"/api/events/{self.event.id}/register/", {}, format="json")
        self.assertEqual(res.status_code, 201)
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.PENDING)

    def test_application_approve_reject_waitlist_and_capacity(self):
        self.auth(self.volunteer)
        app_id = self.client.post(f"/api/events/{self.event.id}/register/", {}, format="json").data["id"]
        v2 = self.make_user("v2@test.in", Role.VOLUNTEER)
        self.auth(v2)
        app2_id = self.client.post(f"/api/events/{self.event.id}/register/", {}, format="json").data["id"]

        self.auth(self.volunteer)  # volunteers cannot decide
        self.assertEqual(self.client.post(f"/api/applications/{app_id}/approve/").status_code, 403)

        self.auth(self.organizer)
        listing = self.client.get(f"/api/events/{self.event.id}/applications/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data["results"]), 2)
        res = self.client.post(f"/api/applications/{app_id}/approve/")
        self.assertEqual(res.data["status"], "APPROVED")
        self.assertTrue(Notification.objects.filter(recipient=self.volunteer, notification_type="APPLICATION_APPROVED").exists())
        full = self.client.post(f"/api/applications/{app2_id}/approve/")
        self.assertEqual(full.status_code, 400)
        self.assertEqual(full.data["code"], "full")
        self.assertEqual(self.client.post(f"/api/applications/{app2_id}/waitlist/").data["status"], "WAITLISTED")
        self.assertEqual(self.client.post(f"/api/applications/{app2_id}/reject/").data["status"], "REJECTED")
        self.assertTrue(Notification.objects.filter(recipient=v2, notification_type="APPLICATION_REJECTED").exists())
        self.assertTrue(Notification.objects.filter(recipient=v2, notification_type="APPLICATION_WAITLISTED").exists())

    def test_registration_when_full_is_waitlisted(self):
        EventApplication.objects.create(volunteer=self.make_user("x@test.in", Role.VOLUNTEER), event=self.event, email="x@test.in", status=ApplicationStatus.APPROVED)
        self.auth(self.volunteer)
        res = self.client.post(f"/api/events/{self.event.id}/register/", {}, format="json")
        self.assertEqual(res.data["status"], "WAITLISTED")

    def test_group_application_accept(self):
        self.auth(self.coordinator)
        res = self.client.post(f"/api/events/{self.event.id}/group-apply/", {"requested_volunteer_count": 3, "message": "We can come", "skills": ["Cleaning"]}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(self.client.post(f"/api/events/{self.event.id}/group-apply/", {"requested_volunteer_count": 3}, format="json").status_code, 409)
        self.auth(self.organizer)
        ga = self.client.get(f"/api/events/{self.event.id}/group-applications/").data[0]
        res = self.client.post(f"/api/group-applications/{ga['id']}/accept/")
        self.assertEqual(res.data["status"], "ACCEPTED")
        self.assertTrue(Notification.objects.filter(recipient=self.volunteer, notification_type="NSS_INVITATION").exists())

    def test_emergency_request_notifies(self):
        self.auth(self.organizer)
        res = self.client.post("/api/emergency-requests/", {
            "title": "Need 5 more", "description": "Urgent", "event": self.event.id, "required_volunteers": 5,
            "location": "Juhu", "priority": "HIGH", "expires_at": "2099-01-01T10:00:00Z",
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(Notification.objects.filter(recipient=self.volunteer, notification_type="EMERGENCY_REQUEST").exists())
