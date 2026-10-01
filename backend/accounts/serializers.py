from decimal import Decimal
import re

from django.contrib.auth import authenticate, password_validation
from django.db import transaction
from rest_framework import serializers

from events.models import EventSkill
from nss_units.models import College, NSSUnit, University, VerificationStatus

from core.validators import validate_image_file

from .models import SELF_REGISTER_ROLES, Gender, Role, User, UserProfile, VolunteerProfile

VALID_INTERESTS = {"ABP1", "ABP2", "COLLEGE_EVENT", "UNIVERSITY_EVENT", "ENVIRONMENT", "COMMUNITY", "HEALTH", "EDUCATION", "AWARENESS"}
PHONE_RE = re.compile(r"^\+?[0-9 \-]{7,20}$")


def validate_phone(value):
    if value and not PHONE_RE.match(value):
        raise serializers.ValidationError("Enter a valid phone number.")
    return value


def skills_from_names(names):
    skills = []
    for name in names or []:
        name = str(name).strip()
        if name:
            skill, _ = EventSkill.objects.get_or_create(name=name.title())
            skills.append(skill)
    return skills


class SkillListField(serializers.ListField):
    """Accepts ["Teaching", "First Aid"] or "Teaching, First Aid"; returns names."""

    child = serializers.CharField(max_length=80)

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = [data]
        flat = []
        for item in data:
            flat.extend(part.strip() for part in str(item).split(","))
        return super().to_internal_value([s for s in flat if s])

    def to_representation(self, value):
        if hasattr(value, "all"):
            return [s.name for s in value.all()]
        return list(value)


def unique_username(email):
    base = re.sub(r"[^a-zA-Z0-9_.@+-]", "", email.split("@")[0])[:120] or "user"
    candidate, i = base, 1
    while User.objects.filter(username=candidate).exists():
        i += 1
        candidate = f"{base}{i}"
    return candidate


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False, default="")
    role = serializers.ChoiceField(choices=[(r.value, r.label) for r in Role if r in SELF_REGISTER_ROLES], default=Role.VOLUNTEER)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="", validators=[validate_phone])
    gender = serializers.ChoiceField(choices=Gender.choices, required=False, default=Gender.UNDISCLOSED)
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all(), required=False, allow_null=True)
    college = serializers.PrimaryKeyRelatedField(queryset=College.objects.all(), required=False, allow_null=True)
    nss_unit = serializers.PrimaryKeyRelatedField(queryset=NSSUnit.objects.all(), required=False, allow_null=True)
    skills = SkillListField(required=False, default=list)
    interests = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    availability = serializers.ListField(child=serializers.ChoiceField(choices=VolunteerProfile.WEEKDAYS), required=False, default=list)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_interests(self, value):
        bad = [v for v in value if v not in VALID_INTERESTS]
        if bad:
            raise serializers.ValidationError(f"Unknown interest(s): {', '.join(bad)}")
        return value

    def validate(self, attrs):
        user = User(email=attrs["email"], first_name=attrs["first_name"], last_name=attrs.get("last_name", ""))
        password_validation.validate_password(attrs["password"], user)
        unit = attrs.get("nss_unit")
        if unit:
            if unit.verification_status in (VerificationStatus.REJECTED, VerificationStatus.SUSPENDED):
                raise serializers.ValidationError({"nss_unit": "This NSS unit is not accepting members."})
            attrs["college"] = unit.college
            attrs["university"] = unit.university
        college = attrs.get("college")
        if college:
            if attrs.get("university") and attrs["university"].id != college.university_id:
                raise serializers.ValidationError({"college": "College does not belong to the selected university."})
            attrs["university"] = college.university
        return attrs

    @transaction.atomic
    def create(self, data):
        user = User.objects.create_user(
            username=unique_username(data["email"]),
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data.get("last_name", ""),
            role=data["role"],
            phone=data.get("phone", ""),
            gender=data.get("gender", Gender.UNDISCLOSED),
        )
        profile = user.profile
        profile.university = data.get("university")
        profile.college = data.get("college")
        profile.city = data.get("city", "")
        profile.save()
        if user.role == Role.VOLUNTEER:
            vp = user.volunteer_profile
            vp.nss_unit = data.get("nss_unit")
            vp.interests = data.get("interests", [])
            vp.availability = data.get("availability", [])
            vp.save()
            vp.skills.set(skills_from_names(data.get("skills")))
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        user = authenticate(self.context.get("request"), email=email, password=attrs["password"])
        if user is None:
            # Distinguish suspended accounts without leaking whether an email exists.
            existing = User.objects.filter(email__iexact=email).first()
            if existing and not existing.is_active and existing.check_password(attrs["password"]):
                raise serializers.ValidationError("This account has been suspended. Contact an administrator.")
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs


class UniversityMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ["id", "name", "short_name"]


class CollegeMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ["id", "name", "university"]


class NSSUnitMiniSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source="college.name", read_only=True)

    class Meta:
        model = NSSUnit
        fields = ["id", "unit_number", "college", "college_name", "verification_status"]


class UserProfileSerializer(serializers.ModelSerializer):
    university_detail = UniversityMiniSerializer(source="university", read_only=True)
    college_detail = CollegeMiniSerializer(source="college", read_only=True)

    class Meta:
        model = UserProfile
        fields = ["photo", "bio", "city", "latitude", "longitude", "university", "college", "university_detail", "college_detail"]
        read_only_fields = ["photo"]


class VolunteerProfileSerializer(serializers.ModelSerializer):
    skills = SkillListField(required=False)
    nss_unit_detail = NSSUnitMiniSerializer(source="nss_unit", read_only=True)

    class Meta:
        model = VolunteerProfile
        fields = ["nss_unit", "nss_unit_detail", "roll_number", "year_of_study", "skills", "interests", "availability"]

    def validate_interests(self, value):
        bad = [v for v in value if v not in VALID_INTERESTS]
        if bad:
            raise serializers.ValidationError(f"Unknown interest(s): {', '.join(bad)}")
        return value

    def validate_availability(self, value):
        bad = [v for v in value if v not in VolunteerProfile.WEEKDAYS]
        if bad:
            raise serializers.ValidationError(f"Unknown weekday(s): {', '.join(bad)}")
        return value


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    volunteer_profile = serializers.SerializerMethodField()
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    full_name = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name", "role", "role_display", "phone", "gender",
            "is_email_verified", "is_active", "date_joined", "last_login", "profile", "volunteer_profile",
            "organization", "photo_url",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email

    def get_volunteer_profile(self, obj):
        vp = getattr(obj, "volunteer_profile", None) if obj.role == Role.VOLUNTEER else None
        return VolunteerProfileSerializer(vp).data if vp else None

    def get_photo_url(self, obj):
        prof = getattr(obj, "profile", None)
        if prof and prof.photo:
            request = self.context.get("request")
            return request.build_absolute_uri(prof.photo.url) if request else prof.photo.url
        return None

    def get_organization(self, obj):
        """Badge text shown in the header: NGO name, NSS unit, college or university."""
        if obj.role == Role.NGO_ORGANIZER:
            ngo = obj.ngos.first()
            return {"type": "NGO", "id": ngo.id, "name": ngo.name, "status": ngo.verification_status} if ngo else None
        if obj.role == Role.NSS_COORDINATOR:
            unit = obj.coordinated_units.select_related("college").first()
            return {"type": "NSS_UNIT", "id": unit.id, "name": str(unit), "status": unit.verification_status} if unit else None
        if obj.role == Role.VOLUNTEER:
            vp = getattr(obj, "volunteer_profile", None)
            if vp and vp.nss_unit_id:
                return {"type": "NSS_UNIT", "id": vp.nss_unit_id, "name": str(vp.nss_unit), "status": vp.nss_unit.verification_status}
        prof = getattr(obj, "profile", None)
        if prof and prof.college_id:
            return {"type": "COLLEGE", "id": prof.college_id, "name": prof.college.name}
        if prof and prof.university_id:
            return {"type": "UNIVERSITY", "id": prof.university_id, "name": prof.university.name}
        return None


class ProfileUpdateSerializer(serializers.Serializer):
    """PATCH /api/auth/profile/ – user fields, profile fields and volunteer fields in one payload."""

    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, validators=[validate_phone])
    gender = serializers.ChoiceField(choices=Gender.choices, required=False)
    bio = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True, min_value=Decimal("-90"), max_value=Decimal("90"))
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True, min_value=Decimal("-180"), max_value=Decimal("180"))
    college = serializers.PrimaryKeyRelatedField(queryset=College.objects.all(), required=False, allow_null=True)
    nss_unit = serializers.PrimaryKeyRelatedField(queryset=NSSUnit.objects.all(), required=False, allow_null=True)
    roll_number = serializers.CharField(max_length=40, required=False, allow_blank=True)
    year_of_study = serializers.IntegerField(min_value=1, max_value=10, required=False, allow_null=True)
    skills = SkillListField(required=False)
    interests = serializers.ListField(child=serializers.CharField(), required=False)
    availability = serializers.ListField(child=serializers.ChoiceField(choices=VolunteerProfile.WEEKDAYS), required=False)

    def validate_interests(self, value):
        bad = [v for v in value if v not in VALID_INTERESTS]
        if bad:
            raise serializers.ValidationError(f"Unknown interest(s): {', '.join(bad)}")
        return value

    def validate_nss_unit(self, unit):
        if unit and unit.verification_status in (VerificationStatus.REJECTED, VerificationStatus.SUSPENDED):
            raise serializers.ValidationError("This NSS unit is not accepting members.")
        return unit

    @transaction.atomic
    def update(self, user, data):
        for f in ("first_name", "last_name", "phone", "gender"):
            if f in data:
                setattr(user, f, data[f])
        user.save()
        prof = user.profile
        for f in ("bio", "city", "latitude", "longitude"):
            if f in data:
                setattr(prof, f, data[f])
        # Admins' college/university scope is set by super admins only.
        if "college" in data and user.role not in (Role.COLLEGE_ADMIN, Role.UNIVERSITY_ADMIN, Role.SUPER_ADMIN):
            prof.college = data["college"]
            prof.university = data["college"].university if data["college"] else prof.university
        if user.role == Role.VOLUNTEER:
            vp = user.volunteer_profile
            if "nss_unit" in data:
                vp.nss_unit = data["nss_unit"]
                if data["nss_unit"]:
                    prof.college = data["nss_unit"].college
                    prof.university = data["nss_unit"].university
            for f in ("roll_number", "year_of_study", "interests", "availability"):
                if f in data:
                    setattr(vp, f, data[f])
            vp.save()
            if "skills" in data:
                vp.skills.set(skills_from_names(data["skills"]))
        prof.save()
        return user


class PhotoUploadSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=True, validators=[validate_image_file])

    class Meta:
        model = UserProfile
        fields = ["photo"]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)


class AdminUserUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Role.choices, required=False)
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all(), required=False, allow_null=True)
    college = serializers.PrimaryKeyRelatedField(queryset=College.objects.all(), required=False, allow_null=True)
    is_email_verified = serializers.BooleanField(required=False)
