import io
import re

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from accounts.models import Role, User

from .base import PASSWORD, BaseAPITest


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "purple").save(buf, format="PNG")
    return buf.getvalue()


class RegistrationTests(BaseAPITest):
    payload = {"email": "New.Student@Test.in", "password": PASSWORD, "first_name": "New", "last_name": "Student", "role": "VOLUNTEER",
               "skills": ["Teaching", "first aid"], "interests": ["ABP1"], "availability": ["SAT"]}

    def test_register_creates_user_profiles_and_sends_verification(self):
        res = self.client.post("/api/auth/register/", {**self.payload, "nss_unit": self.unit.id}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        user = User.objects.get(email="new.student@test.in")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith(("pbkdf2_", "argon2", "bcrypt")))
        self.assertFalse(user.is_email_verified)
        self.assertEqual(user.volunteer_profile.nss_unit, self.unit)
        self.assertEqual(user.profile.college, self.college)
        self.assertEqual(sorted(user.volunteer_profile.skills.values_list("name", flat=True)), ["First Aid", "Teaching"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/verify-email?uid=", mail.outbox[0].body)
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.volunteer_count, 2)

    def test_duplicate_email_rejected(self):
        self.client.post("/api/auth/register/", self.payload, format="json")
        res = self.client.post("/api/auth/register/", self.payload, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data)

    def test_cannot_self_register_as_admin(self):
        res = self.client.post("/api/auth/register/", {**self.payload, "role": "SUPER_ADMIN"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_weak_password_rejected(self):
        res = self.client.post("/api/auth/register/", {**self.payload, "password": "password"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_email_verification_then_login(self):
        self.client.post("/api/auth/register/", self.payload, format="json")
        res = self.login("new.student@test.in")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data["code"], "email_not_verified")
        uid, token = re.search(r"uid=([^&]+)&token=(\S+)", mail.outbox[0].body).groups()
        self.assertEqual(self.client.post("/api/auth/verify-email/", {"uid": uid, "token": "bad-token"}).status_code, 400)
        res = self.client.post("/api/auth/verify-email/", {"uid": uid, "token": token})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.login("new.student@test.in").status_code, 200)


class LoginTests(BaseAPITest):
    def test_login_returns_jwt_and_sets_httponly_cookie(self):
        res = self.login("vol@test.in")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)
        self.assertEqual(res.data["user"]["role"], "VOLUNTEER")
        cookie = res.cookies["nss_refresh"]
        self.assertTrue(cookie["httponly"])
        prof = self.client.get("/api/auth/profile/")
        self.assertEqual(prof.status_code, 200)
        self.assertEqual(prof.data["email"], "vol@test.in")

    def test_wrong_password(self):
        self.assertEqual(self.login("vol@test.in", "nope-nope-1").status_code, 400)

    def test_refresh_and_logout_blacklists(self):
        res = self.login("vol@test.in")
        refresh = res.data["refresh"]
        r2 = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("access", r2.data)
        # rotated: old refresh is blacklisted
        self.assertEqual(self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json").status_code, 401)
        self.client.post("/api/auth/logout/", {"refresh": r2.data["refresh"]}, format="json")
        self.assertEqual(self.client.post("/api/auth/token/refresh/", {"refresh": r2.data["refresh"]}, format="json").status_code, 401)

    def test_refresh_from_cookie(self):
        self.login("vol@test.in")
        self.client.credentials()
        res = self.client.post("/api/auth/token/refresh/", {}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_suspended_user_cannot_login(self):
        self.auth(self.super)
        self.assertEqual(self.client.post(f"/api/admin/users/{self.volunteer.id}/suspend/").status_code, 200)
        res = self.login("vol@test.in")
        self.assertEqual(res.status_code, 400)
        self.assertIn("suspended", str(res.data))

    def test_forgot_and_reset_password(self):
        res = self.client.post("/api/auth/forgot-password/", {"email": "vol@test.in"})
        self.assertEqual(res.status_code, 200)
        uid, token = re.search(r"uid=([^&]+)&token=(\S+)", mail.outbox[-1].body).groups()
        res = self.client.post("/api/auth/reset-password/", {"uid": uid, "token": token, "new_password": "Brand-New-Pass-42"})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(self.login("vol@test.in", "Brand-New-Pass-42").status_code, 200)
        # token single-use
        self.assertEqual(self.client.post("/api/auth/reset-password/", {"uid": uid, "token": token, "new_password": "Another-Pass-77"}).status_code, 400)

    def test_forgot_password_does_not_leak_accounts(self):
        res = self.client.post("/api/auth/forgot-password/", {"email": "nobody@test.in"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)


class ProfileTests(BaseAPITest):
    def test_profile_update(self):
        self.auth(self.volunteer)
        res = self.client.patch("/api/auth/profile/", {"first_name": "Riya", "skills": "Teaching, Photography", "availability": ["SUN"],
                                                       "interests": ["ABP2", "HEALTH"], "city": "Mumbai"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.volunteer.refresh_from_db()
        self.assertEqual(self.volunteer.first_name, "Riya")
        self.assertEqual(self.volunteer.volunteer_profile.availability, ["SUN"])
        self.assertEqual(res.data["volunteer_profile"]["skills"], ["Photography", "Teaching"])

    def test_invalid_interest_rejected(self):
        self.auth(self.volunteer)
        self.assertEqual(self.client.patch("/api/auth/profile/", {"interests": ["HACKING"]}, format="json").status_code, 400)

    def test_photo_upload_valid_image(self):
        self.auth(self.volunteer)
        f = SimpleUploadedFile("me.png", png_bytes(), content_type="image/png")
        res = self.client.post("/api/auth/profile/photo/", {"photo": f}, format="multipart")
        self.assertEqual(res.status_code, 200, res.data)
        self.volunteer.profile.refresh_from_db()
        name = self.volunteer.profile.photo.name
        self.assertTrue(name.startswith("profiles/") and name.endswith(".png"))
        self.assertNotIn("me", name.split("/")[-1])  # random safe filename

    def test_photo_upload_rejects_disguised_executable(self):
        self.auth(self.volunteer)
        f = SimpleUploadedFile("evil.png", b"MZ\x90\x00" + b"\x00" * 100, content_type="image/png")
        res = self.client.post("/api/auth/profile/photo/", {"photo": f}, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_photo_upload_rejects_bad_extension(self):
        self.auth(self.volunteer)
        f = SimpleUploadedFile("me.gif", png_bytes(), content_type="image/gif")
        self.assertEqual(self.client.post("/api/auth/profile/photo/", {"photo": f}, format="multipart").status_code, 400)

    def test_profile_requires_auth(self):
        self.assertEqual(self.client.get("/api/auth/profile/").status_code, 401)
