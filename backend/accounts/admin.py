from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserProfile, VolunteerProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    raw_id_fields = ["university", "college"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "first_name", "last_name", "role", "is_email_verified", "is_active", "date_joined"]
    list_filter = ["role", "is_active", "is_email_verified", "gender", "is_staff"]
    search_fields = ["email", "first_name", "last_name", "username", "phone"]
    ordering = ["-date_joined"]
    readonly_fields = ["date_joined", "last_login"]
    inlines = [UserProfileInline]
    fieldsets = BaseUserAdmin.fieldsets + (("NSS Connect", {"fields": ("role", "phone", "gender", "is_email_verified")}),)
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "username", "role", "password1", "password2")}),
    )
    actions = ["suspend_users", "activate_users"]

    @admin.action(description="Suspend selected accounts")
    def suspend_users(self, request, queryset):
        queryset.exclude(pk=request.user.pk).update(is_active=False)

    @admin.action(description="Activate selected accounts")
    def activate_users(self, request, queryset):
        queryset.update(is_active=True)


@admin.register(VolunteerProfile)
class VolunteerProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "nss_unit", "roll_number", "year_of_study", "created_at"]
    list_filter = ["nss_unit__college", "year_of_study"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "roll_number"]
    raw_id_fields = ["user", "nss_unit"]
    filter_horizontal = ["skills"]
    readonly_fields = ["created_at", "updated_at"]
