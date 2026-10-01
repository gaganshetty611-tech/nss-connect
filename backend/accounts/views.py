import logging

import requests
from django.conf import settings
from django.contrib.auth import password_validation
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from core.permissions import IsPlatformAdmin, is_super, scope_q
from core.utils import frontend_base_url
from notifications.services import send_email

from .models import Role, User
from .serializers import (
    AdminUserUpdateSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PhotoUploadSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
    unique_username,
)
from .tokens import decode_uid, email_verification_token, encode_uid, password_reset_token

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- token helpers
def _set_refresh_cookie(response, refresh):
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path="/api/auth/",
    )


def _clear_refresh_cookie(response):
    response.delete_cookie(settings.JWT_REFRESH_COOKIE, path="/api/auth/", samesite=settings.JWT_COOKIE_SAMESITE)


def issue_tokens(user, request, status_code=status.HTTP_200_OK):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    data = {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user, context={"request": request}).data,
    }
    response = Response(data, status=status_code)
    _set_refresh_cookie(response, refresh)
    return response


def send_verification_email(user, request=None):
    link = f"{frontend_base_url(request)}/verify-email?uid={encode_uid(user)}&token={email_verification_token.make_token(user)}"
    body = (
        f"Hi {user.first_name or user.email},\n\n"
        f"Welcome to NSS Connect! Please verify your email address by opening this link:\n\n{link}\n\n"
        "If you did not create this account you can ignore this email."
    )
    return send_email(user.email, "[NSS Connect] Verify your email", body)


# ---------------------------------------------------------------- auth endpoints
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        if not settings.REQUIRE_EMAIL_VERIFICATION:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
        else:
            send_verification_email(user, request)
        return Response(
            {
                "user": UserSerializer(user, context={"request": request}).data,
                "email_verification_required": settings.REQUIRE_EMAIL_VERIFICATION,
                "detail": "Account created. Check your email to verify your address."
                if settings.REQUIRE_EMAIL_VERIFICATION
                else "Account created. You can log in now.",
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_email_verified:
            return Response(
                {"detail": "Please verify your email before logging in.", "code": "email_not_verified"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return issue_tokens(user, request)


class TokenRefreshView(APIView):
    """Accepts the refresh token from the httpOnly cookie or the JSON body."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        raw = request.data.get("refresh") or request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if not raw:
            return Response({"detail": "No refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            old = RefreshToken(raw)
            user = User.objects.filter(pk=old["user_id"], is_active=True).first()
            if user is None:
                raise TokenError("User inactive")
            old.blacklist()
        except TokenError:
            response = Response({"detail": "Session expired. Please log in again."}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response
        return issue_tokens(user, request)


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        raw = request.data.get("refresh") or request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        response = Response({"detail": "Logged out."})
        _clear_refresh_cookie(response)
        return response


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)
        request.user.refresh_from_db()
        return Response(UserSerializer(request.user, context={"request": request}).data)

    put = patch


class ProfilePhotoView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profile = request.user.profile
        serializer = PhotoUploadSerializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        if profile.photo:
            profile.photo.delete(save=False)
        serializer.save()
        return Response(UserSerializer(request.user, context={"request": request}).data)

    def delete(self, request):
        profile = request.user.profile
        if profile.photo:
            profile.photo.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid = decode_uid(request.data.get("uid", ""))
        user = User.objects.filter(pk=uid).first() if uid else None
        if user and user.is_email_verified:
            return Response({"detail": "Email already verified."})
        if not user or not email_verification_token.check_token(user, request.data.get("token", "")):
            return Response({"detail": "Invalid or expired verification link."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
        return Response({"detail": "Email verified. You can now log in."})


class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        email = (request.data.get("email") or "").lower().strip()
        user = User.objects.filter(email__iexact=email, is_email_verified=False, is_active=True).first()
        if user:
            send_verification_email(user, request)
        # Same response either way: do not reveal which emails exist.
        return Response({"detail": "If that account exists and is unverified, a new link has been sent."})


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"], is_active=True).first()
        if user and user.has_usable_password():
            link = f"{frontend_base_url(request)}/reset-password?uid={encode_uid(user)}&token={password_reset_token.make_token(user)}"
            send_email(
                user.email,
                "[NSS Connect] Reset your password",
                f"Hi {user.first_name or user.email},\n\nReset your password using this link:\n\n{link}\n\n"
                "If you did not request this, ignore this email.",
            )
        return Response({"detail": "If an account exists for that email, a reset link has been sent."})


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = decode_uid(serializer.validated_data["uid"])
        user = User.objects.filter(pk=uid, is_active=True).first() if uid else None
        if not user or not password_reset_token.check_token(user, serializer.validated_data["token"]):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)
        password_validation.validate_password(serializer.validated_data["new_password"], user)
        user.set_password(serializer.validated_data["new_password"])
        # A successful reset also proves ownership of the mailbox.
        user.is_email_verified = True
        user.save()
        return Response({"detail": "Password updated. You can now log in."})


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data["current_password"]):
            raise ValidationError({"current_password": "Current password is incorrect."})
        password_validation.validate_password(serializer.validated_data["new_password"], request.user)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Password changed."})


# ---------------------------------------------------------------- Google OAuth (optional)
def google_configured():
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET and settings.GOOGLE_REDIRECT_URI)


class GoogleConfigView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if not google_configured():
            return Response({"enabled": False})
        return Response({"enabled": True, "client_id": settings.GOOGLE_CLIENT_ID, "redirect_uri": settings.GOOGLE_REDIRECT_URI})


class GoogleLoginView(APIView):
    """Authorization-code flow: the SPA redirects to Google, Google redirects back with ?code=,
    the SPA posts the code here and we exchange it server-side using the client secret."""

    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        if not google_configured():
            return Response({"detail": "Google sign-in is not configured on this server."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        code = request.data.get("code")
        if not code:
            return Response({"detail": "Missing authorization code."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token_resp = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                timeout=10,
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]
            info_resp = requests.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            info_resp.raise_for_status()
            info = info_resp.json()
        except Exception:
            logger.exception("Google OAuth exchange failed")
            return Response({"detail": "Google sign-in failed."}, status=status.HTTP_400_BAD_REQUEST)
        if not info.get("email") or not info.get("email_verified"):
            return Response({"detail": "Google account email is not verified."}, status=status.HTTP_400_BAD_REQUEST)
        email = info["email"].lower()
        user = User.objects.filter(email__iexact=email).first()
        created = False
        if user is None:
            user = User.objects.create_user(
                username=unique_username(email),
                email=email,
                password=None,  # unusable password; Google-only until they set one via reset
                first_name=info.get("given_name", ""),
                last_name=info.get("family_name", ""),
                role=Role.VOLUNTEER,
                is_email_verified=True,
            )
            created = True
        if not user.is_active:
            return Response({"detail": "This account has been suspended."}, status=status.HTTP_403_FORBIDDEN)
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
        return issue_tokens(user, request, status.HTTP_201_CREATED if created else status.HTTP_200_OK)


# ---------------------------------------------------------------- admin user management
class AdminUserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.select_related("profile", "profile__college", "profile__university").order_by("-date_joined")
        qs = qs.filter(scope_q(user, "profile__university_id", "profile__college_id"))
        p = self.request.query_params
        if p.get("role"):
            qs = qs.filter(role=p["role"])
        if p.get("active") in ("true", "false"):
            qs = qs.filter(is_active=p["active"] == "true")
        if p.get("search"):
            s = p["search"]
            qs = qs.filter(Q(email__icontains=s) | Q(first_name__icontains=s) | Q(last_name__icontains=s))
        return qs


def _get_scoped_user(request, pk):
    qs = User.objects.filter(scope_q(request.user, "profile__university_id", "profile__college_id"))
    return get_object_or_404(qs, pk=pk)


class AdminUserDetailView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request, pk):
        return Response(UserSerializer(_get_scoped_user(request, pk), context={"request": request}).data)

    def patch(self, request, pk):
        if not is_super(request.user):
            return Response({"detail": "Only super admins can change roles or scopes."}, status=status.HTTP_403_FORBIDDEN)
        target = get_object_or_404(User, pk=pk)
        serializer = AdminUserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "role" in data:
            if target == request.user and data["role"] != Role.SUPER_ADMIN:
                return Response({"detail": "You cannot demote yourself."}, status=status.HTTP_400_BAD_REQUEST)
            target.role = data["role"]
        if "is_email_verified" in data:
            target.is_email_verified = data["is_email_verified"]
        target.save()
        prof = target.profile
        if "university" in data:
            prof.university = data["university"]
        if "college" in data:
            prof.college = data["college"]
            if data["college"]:
                prof.university = data["college"].university
        prof.save()
        return Response(UserSerializer(target, context={"request": request}).data)


class AdminUserSuspendView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk, action):
        target = _get_scoped_user(request, pk)
        if target == request.user:
            return Response({"detail": "You cannot suspend your own account."}, status=status.HTTP_400_BAD_REQUEST)
        if target.is_platform_admin and not is_super(request.user):
            return Response({"detail": "Only super admins can suspend administrators."}, status=status.HTTP_403_FORBIDDEN)
        target.is_active = action == "activate"
        target.save(update_fields=["is_active"])
        if not target.is_active:
            # Kill all outstanding refresh tokens.
            from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

            for tok in OutstandingToken.objects.filter(user=target):
                BlacklistedToken.objects.get_or_create(token=tok)
        if hasattr(target, "volunteer_profile") and target.volunteer_profile.nss_unit_id:
            target.volunteer_profile.nss_unit.refresh_volunteer_count()
        return Response(UserSerializer(target, context={"request": request}).data)
