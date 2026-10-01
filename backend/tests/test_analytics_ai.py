from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from accounts.models import Gender, Role
from ai_matching.models import AIRecommendation
from ai_matching.providers import RuleBasedAIProvider
from attendance.models import Attendance, VolunteerHours
from certificates.models import Certificate
from events.models import ApplicationStatus, EventApplication, EventStatus, EventSkill
from nss_units.models import College, NSSUnit, VerificationStatus

from .base import BaseAPITest


class AnalyticsTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.volunteer.gender = Gender.FEMALE
        self.volunteer.save()
        self.e1 = self.make_event(category="ABP1", status=EventStatus.COMPLETED, starts_in=-timedelta(days=5))
        self.e2 = self.make_event(category="ABP2", status=EventStatus.COMPLETED, starts_in=-timedelta(days=3))
        self.e3 = self.make_event(category="COLLEGE_EVENT", starts_in=timedelta(days=3))
        self.make_event(category="ABP1", status=EventStatus.PENDING)  # must not be counted
        for e, st, h in [(self.e1, "PRESENT", "3.00"), (self.e2, "ABSENT", None)]:
            EventApplication.objects.create(volunteer=self.volunteer, event=e, email="v@test.in", status=ApplicationStatus.APPROVED)
            att = Attendance.objects.create(volunteer=self.volunteer, event=e, status=st, check_in=timezone.now() if h else None)
            if h:
                VolunteerHours.objects.create(volunteer=self.volunteer, event=e, attendance=att, hours=Decimal(h), category=e.category, verified=True)

    def test_analytics_from_database(self):
        res = self.client.get("/api/analytics/")
        self.assertEqual(res.status_code, 200)
        s = res.data["summary"]
        self.assertEqual(s["total_events"], 3)
        self.assertEqual((s["abp1_events"], s["abp2_events"], s["college_events"], s["university_events"]), (1, 1, 1, 0))
        self.assertEqual(s["volunteer_hours"], 3.0)
        self.assertEqual(s["attendance_rate"], 50.0)
        self.assertEqual(s["completed_drives"], 2)
        self.assertEqual(s["total_volunteers"], 1)
        charts = res.data["charts"]
        for key in ("events_by_category", "monthly_events", "volunteer_participation", "attendance_trends", "college_participation", "abp_comparison"):
            self.assertIn(key, charts)
        self.assertEqual(charts["university_gender"][0]["female"], 1)
        self.assertEqual(self.client.get("/api/analytics/", {"category": "ABP2"}).data["summary"]["total_events"], 1)

    def test_analytics_update_automatically(self):
        before = self.client.get("/api/analytics/").data["summary"]["volunteer_hours"]
        att = Attendance.objects.get(event=self.e2)
        att.status = "PRESENT"
        att.save()
        VolunteerHours.objects.create(volunteer=self.volunteer, event=self.e2, attendance=att, hours=Decimal("2.50"), category="ABP2", verified=True)
        after = self.client.get("/api/analytics/").data["summary"]
        self.assertEqual(after["volunteer_hours"], before + 2.5)
        self.assertEqual(after["attendance_rate"], 100.0)

    def test_volunteer_dashboard(self):
        EventApplication.objects.create(volunteer=self.volunteer, event=self.e3, email="v@test.in", status=ApplicationStatus.APPROVED)
        Certificate.objects.create(volunteer=self.volunteer, event=self.e1, hours=Decimal("3"))
        self.auth(self.volunteer)
        res = self.client.get("/api/dashboard/volunteer/")
        self.assertEqual(res.status_code, 200)
        s = res.data["stats"]
        self.assertEqual(s["events_participated"], 1)
        self.assertEqual(s["upcoming_drives"], 1)
        self.assertEqual(s["registered_events"], 3)
        self.assertEqual(s["volunteer_hours"], 3.0)
        self.assertEqual(s["certificates"], 1)
        self.assertEqual(s["attendance_rate"], 50.0)
        self.assertEqual(s["impact_points"], 3 * 10 + 1 * 20)
        self.assertTrue(next(b for b in s["badges"] if b["code"] == "FIRST_DRIVE")["earned"])
        self.auth(self.organizer)
        self.assertEqual(self.client.get("/api/dashboard/volunteer/").status_code, 403)

    def test_reports_csv_and_pdf(self):
        self.auth(self.super)
        for kind in ("volunteer_participation", "event_participation", "abp1", "abp2", "attendance", "volunteer_hours", "college", "university"):
            res = self.client.get("/api/reports/", {"type": kind, "export": "csv"})
            self.assertEqual(res.status_code, 200, kind)
            self.assertEqual(res["Content-Type"], "text/csv")
        csv_text = self.client.get("/api/reports/", {"type": "abp1", "export": "csv"}).content.decode()
        self.assertIn("Beach Clean-up", csv_text)
        pdf = self.client.get("/api/reports/", {"type": "university", "export": "pdf"})
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertEqual(self.client.get("/api/reports/", {"type": "nope"}).status_code, 400)


class AITests(BaseAPITest):
    def test_categorize(self):
        p = RuleBasedAIProvider()
        self.assertEqual(p.categorize_event("Blood donation camp", "Voluntary blood donation with hospital")["category"], "ABP2")
        r = p.categorize_event("Beach cleanup", "Plastic waste collection")
        self.assertEqual((r["category"], r["theme"]), ("ABP1", "ENVIRONMENT"))
        self.assertEqual(p.categorize_event("Inter-college rally", "university level awareness rally")["category"], "UNIVERSITY_EVENT")
        self.assertIsNone(p.categorize_event("Meeting", "General meeting")["category"])
        self.auth(self.organizer)
        res = self.client.post("/api/ai/categorize/", {"title": "Teaching kids", "description": "tutoring and literacy"}, format="json")
        self.assertEqual(res.data["theme"], "EDUCATION")
        self.assertIn("disclaimer", res.data)

    def test_recommendations_rank_and_explain(self):
        far_college = College.objects.create(university=self.uni, name="Far College")
        far_coord = self.make_user("far@test.in", Role.NSS_COORDINATOR)
        far = NSSUnit.objects.create(college=far_college, unit_number="2", coordinator=far_coord, latitude=Decimal("18.52"),
                                     longitude=Decimal("73.85"), verification_status=VerificationStatus.VERIFIED)  # Pune ~120 km
        NSSUnit.objects.create(college=far_college, unit_number="3", verification_status=VerificationStatus.PENDING)  # excluded
        skill = EventSkill.objects.create(name="Tree Plantation")
        vp = self.volunteer.volunteer_profile
        vp.skills.add(skill)
        vp.interests = ["ABP1"]
        vp.save()
        event = self.make_event(starts_in=timedelta(days=3))
        event.required_skills.add(skill)
        self.auth(self.organizer)
        res = self.client.get(f"/api/events/{event.id}/recommendations/")
        self.assertEqual(res.status_code, 200, res.data)
        results = res.data["results"]
        self.assertEqual([r["nss_unit_id"] for r in results], [self.unit.id, far.id])
        top = results[0]
        self.assertGreater(Decimal(top["match_score"]), Decimal(results[1]["match_score"]))
        self.assertEqual(Decimal(top["skill_score"]), Decimal("100"))
        self.assertTrue(any("km from the venue" in r for r in top["reasons"]))
        self.assertEqual(Decimal(results[1]["distance_score"]), Decimal("0"))
        self.assertIn("disclaimer", res.data)
        self.assertEqual(AIRecommendation.objects.filter(event=event).count(), 2)
        self.auth(self.volunteer)
        self.assertEqual(self.client.get(f"/api/events/{event.id}/recommendations/").status_code, 403)

    def test_turnout_and_datetime_suggestion(self):
        past = self.make_event(status=EventStatus.COMPLETED, starts_in=-timedelta(days=7))
        v2 = self.make_user("v2@test.in", Role.VOLUNTEER)
        for v, st in [(self.volunteer, "PRESENT"), (v2, "ABSENT")]:
            EventApplication.objects.create(volunteer=v, event=past, email="x@test.in", status=ApplicationStatus.APPROVED)
            Attendance.objects.create(volunteer=v, event=past, status=st)
        upcoming = self.make_event(starts_in=timedelta(days=4))
        for i in range(4):
            EventApplication.objects.create(volunteer=self.make_user(f"n{i}@test.in", Role.VOLUNTEER), event=upcoming, email="n@test.in", status=ApplicationStatus.APPROVED)
        self.auth(self.organizer)
        est = self.client.get(f"/api/events/{upcoming.id}/turnout-estimate/").data
        self.assertEqual(est["historical_show_rate"], 50.0)
        self.assertEqual(est["expected_turnout"], 2)
        sug = self.client.get("/api/ai/suggest-datetime/", {"category": "ABP1"}).data
        self.assertEqual(sug["suggestions"][0]["turnout_rate"], 50.0)
        self.assertEqual(sug["suggestions"][0]["events_considered"], 1)

    def test_summary(self):
        past = self.make_event(status=EventStatus.COMPLETED, starts_in=-timedelta(days=1))
        self.auth(self.organizer)
        res = self.client.post(f"/api/events/{past.id}/summary/", {"organizer_notes": "Collected 40 kg plastic."}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Collected 40 kg plastic.", res.data["summary"])
        past.refresh_from_db()
        self.assertEqual(past.summary, res.data["summary"])
