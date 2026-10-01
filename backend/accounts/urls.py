from django.urls import path, re_path

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/token/refresh/", views.TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/profile/", views.ProfileView.as_view(), name="auth-profile"),
    path("auth/profile/photo/", views.ProfilePhotoView.as_view(), name="auth-profile-photo"),
    path("auth/verify-email/", views.VerifyEmailView.as_view(), name="auth-verify-email"),
    path("auth/resend-verification/", views.ResendVerificationView.as_view(), name="auth-resend-verification"),
    path("auth/forgot-password/", views.ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("auth/reset-password/", views.ResetPasswordView.as_view(), name="auth-reset-password"),
    path("auth/change-password/", views.ChangePasswordView.as_view(), name="auth-change-password"),
    path("auth/google/config/", views.GoogleConfigView.as_view(), name="auth-google-config"),
    path("auth/google/", views.GoogleLoginView.as_view(), name="auth-google"),
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", views.AdminUserDetailView.as_view(), name="admin-user-detail"),
    re_path(r"^admin/users/(?P<pk>\d+)/(?P<action>suspend|activate)/$", views.AdminUserSuspendView.as_view(), name="admin-user-action"),
]
