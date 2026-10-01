"""
python manage.py seed_demo_data [--reset]

Creates realistic, relational demo data. Every dashboard number is then *computed* from these rows
(no statistic is stored separately). Past drives go through the real services (check-out → hours →
feedback → certificate PDF) so the data is exactly what the live workflow would produce.

All demo accounts use the password printed at the end.
"""
import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Gender, Role, User
from accounts.serializers import skills_from_names
from attendance import services as att_services
from attendance.models import Attendance, EventQR
from core.utils import event_window
from events.models import (
    ApplicationStatus,
    EmergencyVolunteerRequest,
    Event,
    EventApplication,
    EventStatus,
    GroupApplication,
)
from ngos.models import NGO, VerificationDocument
from notifications.models import NotificationType
from notifications.services import notify
from nss_units.models import College, NSSUnit, University, VerificationStatus

PASSWORD = "NssDemo@2026"

VOLUNTEERS = [
    # first, last, gender, unit_idx, skills, interests, availability
    ("Aarav", "Mehta", Gender.MALE, 0, ["Teaching", "Public Speaking"], ["ABP2", "EDUCATION"], ["SAT", "SUN"]),
    ("Diya", "Iyer", Gender.FEMALE, 0, ["First Aid", "Event Management"], ["ABP2", "HEALTH"], ["SAT", "SUN", "WED"]),
    ("Rohan", "Patil", Gender.MALE, 0, ["Tree Plantation", "Physical Work"], ["ABP1", "ENVIRONMENT"], ["SAT", "SUN"]),
    ("Sneha", "Kulkarni", Gender.FEMALE, 0, ["Photography", "Social Media"], ["ABP1", "COMMUNITY"], ["SUN"]),
    ("Kabir", "Shaikh", Gender.MALE, 1, ["Teaching", "Computer Skills"], ["ABP2", "EDUCATION"], ["SAT", "FRI"]),
    ("Ananya", "Nair", Gender.FEMALE, 1, ["First Aid", "Counselling"], ["ABP2", "HEALTH", "AWARENESS"], ["SAT", "SUN"]),
    ("Vivek", "Rao", Gender.MALE, 1, ["Physical Work", "Waste Segregation"], ["ABP1", "ENVIRONMENT"], ["SUN", "SAT"]),
    ("Meera", "Deshpande", Gender.FEMALE, 2, ["Street Play", "Public Speaking"], ["ABP2", "AWARENESS"], ["SAT"]),
    ("Pooja", "Joshi", Gender.FEMALE, 2, ["Teaching", "Photography"], ["ABP2", "EDUCATION", "COLLEGE_EVENT"], ["SAT", "SUN"]),
    ("Isha", "Kapoor", Gender.FEMALE, 2, ["Tree Plantation", "Event Management"], ["ABP1", "UNIVERSITY_EVENT"], ["SUN"]),
]


class Command(BaseCommand):
    help = "Seed realistic demo data (10 volunteers, 3 NGOs, 3 NSS units, 10 events, applications, attendance, certificates…)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Flush the database first (DESTROYS ALL DATA).")

    def handle(self, *args, reset=False, **opts):
        if reset:
            call_command("flush", interactive=False, verbosity=0)
        if User.objects.filter(email="admin@nssconnect.local").exists():
            raise CommandError("Demo data already exists. Use --reset to recreate it (this wipes the database).")
        random.seed(42)
        from django.test.utils import override_settings

        # Don't spam the console/SMTP with hundreds of demo emails; in-app notifications are still created.
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"), transaction.atomic():
            self._seed()
        self.stdout.write(self.style.SUCCESS("\nDemo data created."))
        self.stdout.write(f"All demo accounts use password: {PASSWORD}\n")
        for email, role in [
            ("admin@nssconnect.local", "Super Admin"),
            ("mu.admin@nssconnect.local", "University Admin (University of Mumbai)"),
            ("sies.admin@nssconnect.local", "College Admin (SIES College)"),
            ("coordinator.sies@nssconnect.local", "NSS Coordinator (SIES unit)"),
            ("organizer@greenmumbai.org", "NGO Organizer (Green Mumbai Foundation – verified)"),
            ("organizer@sankalpblood.org", "NGO Organizer (Sankalp – verified)"),
            ("organizer@akshar.org", "NGO Organizer (Akshar – pending verification)"),
            ("aarav.mehta@student.nssconnect.local", "Volunteer (has certificates, approved for today's drive)"),
        ]:
            self.stdout.write(f"  {email:45s} {role}")

    # ------------------------------------------------------------------ helpers
    def user(self, email, first, last, role, gender=Gender.UNDISCLOSED, **extra):
        u = User.objects.create_user(
            username=email, email=email, password=PASSWORD, first_name=first, last_name=last,
            role=role, gender=gender, is_email_verified=True, phone=f"+91 98{random.randint(10000000, 99999999)}",
        )
        for k, v in extra.items():
            setattr(u, k, v)
        u.save()
        return u

    def _seed(self):
        now = timezone.now()
        today = timezone.localdate()

        # ---------------- institutions
        mu = University.objects.create(name="University of Mumbai", short_name="MU", city="Mumbai")
        sndt = University.objects.create(name="SNDT Women's University", short_name="SNDT", city="Mumbai")
        colleges = [
            College.objects.create(university=mu, name="SIES College of Arts, Science and Commerce", code="SIES", city="Sion, Mumbai",
                                   latitude=Decimal("19.043300"), longitude=Decimal("72.863300")),
            College.objects.create(university=mu, name="Ramnarain Ruia Autonomous College", code="RUIA", city="Matunga, Mumbai",
                                   latitude=Decimal("19.026500"), longitude=Decimal("72.849700")),
            College.objects.create(university=sndt, name="SNDT College of Arts and SCB College of Commerce for Women", code="SNDT-CG",
                                   city="Churchgate, Mumbai", latitude=Decimal("18.933800"), longitude=Decimal("72.826700")),
        ]

        # ---------------- admins
        self.user("admin@nssconnect.local", "Platform", "Admin", Role.SUPER_ADMIN, is_staff=True, is_superuser=True)
        mu_admin = self.user("mu.admin@nssconnect.local", "Neha", "Sawant", Role.UNIVERSITY_ADMIN, Gender.FEMALE)
        mu_admin.profile.university = mu
        mu_admin.profile.save()
        sies_admin = self.user("sies.admin@nssconnect.local", "Rajesh", "Pillai", Role.COLLEGE_ADMIN, Gender.MALE)
        sies_admin.profile.college, sies_admin.profile.university = colleges[0], mu
        sies_admin.profile.save()

        # ---------------- NSS units + coordinators
        coord_data = [("coordinator.sies", "Kavita", "Menon", Gender.FEMALE), ("coordinator.ruia", "Suresh", "Gaikwad", Gender.MALE),
                      ("coordinator.sndt", "Farah", "Khan", Gender.FEMALE)]
        units = []
        for i, (handle, first, last, g) in enumerate(coord_data):
            coord = self.user(f"{handle}@nssconnect.local", first, last, Role.NSS_COORDINATOR, g)
            c = colleges[i]
            coord.profile.college, coord.profile.university = c, c.university
            coord.profile.save()
            units.append(NSSUnit.objects.create(
                college=c, university=c.university, unit_number=str(i + 1), coordinator=coord,
                email=f"nss.{c.code.lower()}@college.edu.in", phone=f"+91 22 2400 {1000 + i}", location=c.city,
                latitude=c.latitude, longitude=c.longitude, verification_status=VerificationStatus.VERIFIED,
            ))

        # ---------------- volunteers
        volunteers = []
        for first, last, g, ui, skills, interests, avail in VOLUNTEERS:
            v = self.user(f"{first.lower()}.{last.lower()}@student.nssconnect.local", first, last, Role.VOLUNTEER, g)
            unit = units[ui]
            v.profile.college, v.profile.university = unit.college, unit.university
            v.profile.city = "Mumbai"
            v.profile.save()
            vp = v.volunteer_profile
            vp.nss_unit, vp.interests, vp.availability = unit, interests, avail
            vp.roll_number = f"{unit.college.code}{random.randint(2400, 2499)}"
            vp.year_of_study = random.choice([1, 2, 3])
            vp.save()
            vp.skills.set(skills_from_names(skills))
            volunteers.append(v)

        # ---------------- NGOs
        ngo_specs = [
            ("organizer@greenmumbai.org", "Tanvi", "Shah", "Green Mumbai Foundation",
             "Citizen-led environmental NGO running beach clean-ups, mangrove restoration and urban tree plantation across Mumbai.",
             "Juhu, Mumbai", "19.098800", "72.826500", ["ENVIRONMENT", "COMMUNITY"], VerificationStatus.VERIFIED),
            ("organizer@sankalpblood.org", "Imran", "Qureshi", "Sankalp Blood Donors Trust",
             "Organises voluntary blood donation camps and health check-up drives with city hospitals.",
             "Dadar, Mumbai", "19.018000", "72.842600", ["HEALTH", "AWARENESS"], VerificationStatus.VERIFIED),
            ("organizer@akshar.org", "Priya", "Raman", "Akshar Learning Collective",
             "After-school tutoring and digital literacy for children in Dharavi and Sion Koliwada.",
             "Dharavi, Mumbai", "19.040300", "72.855400", ["EDUCATION"], VerificationStatus.PENDING),
        ]
        ngos = []
        for email, first, last, name, desc, loc, lat, lng, areas, st in ngo_specs:
            owner = self.user(email, first, last, Role.NGO_ORGANIZER)
            ngo = NGO.objects.create(owner=owner, name=name, description=desc, location=loc, latitude=Decimal(lat), longitude=Decimal(lng),
                                     focus_areas=areas, email=email, phone=owner.phone, website=f"https://{email.split('@')[1]}",
                                     registration_number=f"MH/{random.randint(1000, 9999)}/2019", verification_status=st,
                                     verified_at=now if st == VerificationStatus.VERIFIED else None)
            ngos.append(ngo)
            pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF"
            doc = VerificationDocument(ngo=ngo, document_type=VerificationDocument.DocumentType.REGISTRATION_CERTIFICATE,
                                       original_filename="registration-certificate.pdf",
                                       status=VerificationDocument.Status.APPROVED if st == VerificationStatus.VERIFIED else VerificationDocument.Status.PENDING)
            doc.file.save("registration-certificate.pdf", ContentFile(pdf), save=True)
        green, sankalp, akshar = ngos
        coords = [u.coordinator for u in units]

        # ---------------- events (10, all four categories)
        def ev(title, desc, cat, theme, organizer, days, start, end, loc, lat, lng, cap, skills, status, ngo=None, unit=None, **kw):
            e = Event.objects.create(
                title=title, description=desc, category=cat, theme=theme, organizer=organizer, ngo=ngo, nss_unit=unit,
                college=unit.college if unit else None, university=unit.university if unit else None,
                date=today + timedelta(days=days), start_time=start, end_time=end, location=loc,
                latitude=Decimal(lat), longitude=Decimal(lng), maximum_volunteers=cap, contact_email=organizer.email,
                contact_phone=organizer.phone, status=status, meeting_point=kw.get("meeting_point", "Main entrance"),
                requirements=kw.get("requirements", "Carry a water bottle and your college ID."),
                instructions=kw.get("instructions", "Check in by scanning the event QR at the venue; check out before leaving."),
            )
            e.required_skills.set(skills_from_names(skills))
            return e

        C = EventStatus.COMPLETED
        past = [
            ev("Juhu Beach Clean-up Drive", "Morning beach cleanup with waste segregation and plastic audit along Juhu beach.", "ABP1", "ENVIRONMENT",
               green.owner, -52, time(7, 0), time(10, 0), "Juhu Beach, Mumbai", "19.098800", "72.826500", 8, ["Physical Work", "Waste Segregation"], C, ngo=green),
            ev("Blood Donation Camp at Dadar", "Voluntary blood donation camp with Sankalp and KEM Hospital; volunteers manage registration and donor care.",
               "ABP2", "HEALTH", sankalp.owner, -38, time(10, 0), time(15, 0), "Dadar Community Hall", "19.018000", "72.842600", 6, ["First Aid", "Event Management"], C, ngo=sankalp),
            ev("Digital Literacy Workshop for Seniors", "Teaching senior citizens to use UPI, WhatsApp and government service portals safely.", "ABP2", "EDUCATION",
               coords[0], -24, time(14, 0), time(17, 0), "SIES College Seminar Hall, Sion", "19.043300", "72.863300", 6, ["Teaching", "Computer Skills"], C, unit=units[0]),
            ev("Mangrove Plantation at Mahim", "Planting mangrove saplings and clearing debris along Mahim creek with forest department guidance.", "ABP1", "ENVIRONMENT",
               green.owner, -10, time(7, 30), time(11, 30), "Mahim Nature Park", "19.041600", "72.853800", 7, ["Tree Plantation", "Physical Work"], C, ngo=green),
            ev("Inter-College Road Safety Rally", "University-level awareness rally on road safety with street plays at major junctions.", "UNIVERSITY_EVENT", "AWARENESS",
               coords[1], -5, time(9, 0), time(12, 0), "Matunga to Dadar TT Circle", "19.026500", "72.849700", 10, ["Street Play", "Public Speaking"], C, unit=units[1]),
        ]
        start_today = timezone.localtime(now - timedelta(minutes=30))
        end_today = timezone.localtime(now + timedelta(hours=3))
        live = ev("Campus Cleanliness & Waste Audit", "College-level cleanliness drive and dry-waste audit across the SIES campus. (Live demo drive – QR check-in is open now.)",
                  "COLLEGE_EVENT", "ENVIRONMENT", coords[0], (start_today.date() - today).days, start_today.time().replace(second=0, microsecond=0),
                  end_today.time().replace(second=0, microsecond=0), "SIES College Campus, Sion", "19.043300", "72.863300", 12,
                  ["Waste Segregation", "Physical Work"], EventStatus.APPROVED, unit=units[0])
        upcoming = [
            ev("Thalassemia Awareness & Screening Camp", "Awareness session and free thalassemia screening for students with Sankalp Trust.", "ABP2", "HEALTH",
               sankalp.owner, 6, time(10, 0), time(14, 0), "Ruia College Auditorium, Matunga", "19.026500", "72.849700", 10, ["First Aid", "Counselling"], EventStatus.APPROVED, ngo=sankalp),
            ev("Aarey Tree Plantation Weekend", "Native tree plantation with soil preparation and watering schedule set-up in Aarey.", "ABP1", "ENVIRONMENT",
               green.owner, 13, time(7, 0), time(11, 0), "Aarey Colony, Goregaon", "19.155600", "72.872200", 15, ["Tree Plantation"], EventStatus.APPROVED, ngo=green),
            ev("NSS Foundation Day Celebration", "College-level NSS Foundation Day with volunteer recognition and planning for the winter camp.", "COLLEGE_EVENT", "COMMUNITY",
               coords[2], 20, time(11, 0), time(13, 0), "SNDT Churchgate Campus", "18.933800", "72.826700", 20, ["Event Management"], EventStatus.APPROVED, unit=units[2]),
            ev("Community Health Check-up Camp", "Basic health check-up camp in Sion Koliwada; volunteers handle registration and queue management.", "ABP2", "HEALTH",
               sankalp.owner, 27, time(9, 0), time(13, 0), "Sion Koliwada Community Centre", "19.039000", "72.866000", 8, ["First Aid"], EventStatus.PENDING, ngo=sankalp),
        ]

        # ---------------- applications, attendance, hours, feedback, certificates (past drives)
        def apply(v, e, status):
            vp = v.volunteer_profile
            app = EventApplication.objects.create(volunteer=v, event=e, college=v.profile.college, nss_unit=vp.nss_unit, email=v.email,
                                                  phone=v.phone, status=status, decided_at=now if status != ApplicationStatus.PENDING else None,
                                                  decided_by=e.organizer if status != ApplicationStatus.PENDING else None)
            app.skills.set(vp.skills.all())
            return app

        participants = {
            0: [2, 3, 6, 9, 0, 1],       # beach clean-up
            1: [1, 5, 0, 4, 7],          # blood camp
            2: [0, 4, 8, 3],             # digital literacy
            3: [2, 6, 9, 3, 1],          # mangroves
            4: [7, 8, 0, 5, 4, 2, 6],    # road safety rally
        }
        absentees = {(0, 1), (1, 7), (3, 1), (4, 6)}
        no_feedback = {(4, 2)}  # checked out but feedback pending → hours not yet verified
        comments = ["Well organised, learnt a lot.", "Great coordination by the team.", "Would love to join again!",
                    "Briefing could start on time.", "Very meaningful experience."]
        for ei, e in enumerate(past):
            start, end = event_window(e)
            for vi in participants[ei]:
                v = volunteers[vi]
                app = apply(v, e, ApplicationStatus.APPROVED)
                if (ei, vi) in absentees:
                    continue
                late = random.random() < 0.2
                cin = start + timedelta(minutes=random.randint(20, 40) if late else random.randint(-15, 10))
                att = Attendance.objects.create(volunteer=v, event=e, application=app, check_in=cin,
                                                status=Attendance.Status.LATE if late else Attendance.Status.PRESENT)
                cout = end - timedelta(minutes=random.randint(0, 25))
                att_services._record_checkout(att, cout)
                if (ei, vi) not in no_feedback:
                    att_services.submit_feedback(v, e, random.choice([4, 4, 5, 5, 3]), random.choice(comments))
            # one rejected application for realism
            if ei == 1:
                apply(volunteers[9], e, ApplicationStatus.REJECTED)
            att_services.mark_absentees(e)
            from ai_matching.providers import get_provider

            e.organizer_notes = "Drive completed as planned; materials were provided by the host organisation."
            e.summary = get_provider().summarize_event(e)["summary"]
            e.save()

        # ---------------- live drive (today): approved/pending mix + an active QR
        for vi in (0, 1, 2, 3):
            apply(volunteers[vi], live, ApplicationStatus.APPROVED)
        apply(volunteers[8], live, ApplicationStatus.PENDING)
        _, live_end = event_window(live)
        EventQR.objects.create(event=live, expires_at=live_end + timedelta(hours=2), created_by=live.organizer)

        # ---------------- upcoming drives
        apply(volunteers[5], upcoming[0], ApplicationStatus.APPROVED)
        apply(volunteers[1], upcoming[0], ApplicationStatus.PENDING)
        apply(volunteers[4], upcoming[0], ApplicationStatus.PENDING)
        apply(volunteers[2], upcoming[1], ApplicationStatus.APPROVED)
        apply(volunteers[6], upcoming[1], ApplicationStatus.WAITLISTED)
        apply(volunteers[9], upcoming[1], ApplicationStatus.PENDING)
        apply(volunteers[7], upcoming[2], ApplicationStatus.APPROVED)
        c = apply(volunteers[3], upcoming[2], ApplicationStatus.APPROVED)
        c.status = ApplicationStatus.CANCELLED
        c.save()

        GroupApplication.objects.create(nss_unit=units[1], event=upcoming[1], submitted_by=units[1].coordinator, requested_volunteer_count=3,
                                        message="Ruia NSS unit can bring 3 volunteers with plantation experience.")

        EmergencyVolunteerRequest.objects.create(
            title="Extra hands needed for Aarey plantation", description="Saplings delivery doubled – need 5 more volunteers.",
            event=upcoming[1], created_by=green.owner, required_volunteers=5, location="Aarey Colony, Goregaon",
            latitude=Decimal("19.155600"), longitude=Decimal("72.872200"), priority=EmergencyVolunteerRequest.Priority.HIGH,
            expires_at=now + timedelta(days=10),
        )

        # ---------------- a few workflow notifications (the services above created most)
        notify(akshar.owner, NotificationType.NGO_STATUS_CHANGED, "Verification in progress",
               "Your documents were received and are being reviewed by the university admin.", link=f"/ngos/{akshar.id}")
        for admin in User.objects.filter(role__in=[Role.SUPER_ADMIN, Role.UNIVERSITY_ADMIN]):
            notify(admin, NotificationType.EVENT_UPDATED, "New drive awaiting approval",
                   f"{upcoming[3].title} needs review.", link="/admin/events")

        # ---------------- AI recommendations for upcoming drives
        from ai_matching.models import AIRecommendation
        from ai_matching.providers import get_provider

        provider = get_provider()
        for e in [live] + upcoming[:3]:
            for r in provider.recommend_units(e):
                unit = r.pop("nss_unit")
                AIRecommendation.objects.update_or_create(event=e, nss_unit=unit, defaults={**r, "provider": provider.name})
