import datetime

from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import SkillListField, skills_from_names, validate_phone
from core.permissions import can_manage_event

from .models import (
    ApplicationStatus,
    EmergencyVolunteerRequest,
    Event,
    EventApplication,
    EventPhoto,
    EventSkill,
    EventTheme,
    GroupApplication,
)


class EventSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSkill
        fields = ["id", "name"]


class EventListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    theme_display = serializers.CharField(source="get_theme_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    organizer_display = serializers.CharField(read_only=True)
    required_skills = SkillListField(read_only=True)
    approved_count = serializers.IntegerField(read_only=True, default=0)
    spots_left = serializers.SerializerMethodField()
    ngo_verified = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "title", "description", "category", "category_display", "theme", "theme_display", "status",
            "status_display", "date", "start_time", "end_time", "location", "latitude", "longitude",
            "maximum_volunteers", "approved_count", "spots_left", "required_skills", "event_image",
            "organizer_display", "ngo", "ngo_verified", "nss_unit", "created_at",
        ]

    def get_spots_left(self, obj):
        approved = getattr(obj, "approved_count", None)
        if approved is None:
            approved = obj.applications.filter(status__in=[ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED]).count()
        return max(obj.maximum_volunteers - approved, 0)

    def get_ngo_verified(self, obj):
        return bool(obj.ngo_id and obj.ngo.verified)


class EventDetailSerializer(EventListSerializer):
    organizer_name = serializers.CharField(source="organizer.display_name", read_only=True)
    ngo_name = serializers.CharField(source="ngo.name", read_only=True, default=None)
    nss_unit_name = serializers.SerializerMethodField()
    college_name = serializers.CharField(source="college.name", read_only=True, default=None)
    university_name = serializers.CharField(source="university.name", read_only=True, default=None)
    pending_count = serializers.SerializerMethodField()
    waitlisted_count = serializers.SerializerMethodField()
    my_application = serializers.SerializerMethodField()
    my_attendance = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()
    photo_count = serializers.IntegerField(source="photos.count", read_only=True)

    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + [
            "organizer", "organizer_name", "ngo_name", "nss_unit_name", "college", "college_name", "university",
            "university_name", "requirements", "meeting_point", "contact_email", "contact_phone", "instructions",
            "review_note", "summary", "organizer_notes", "pending_count", "waitlisted_count", "my_application",
            "my_attendance", "can_manage", "photo_count", "updated_at",
        ]

    def get_nss_unit_name(self, obj):
        return str(obj.nss_unit) if obj.nss_unit_id else None

    def _user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def get_pending_count(self, obj):
        return obj.applications.filter(status=ApplicationStatus.PENDING).count()

    def get_waitlisted_count(self, obj):
        return obj.applications.filter(status=ApplicationStatus.WAITLISTED).count()

    def get_my_application(self, obj):
        user = self._user()
        if not (user and user.is_authenticated):
            return None
        app = obj.applications.filter(volunteer=user).first()
        return {"id": app.id, "status": app.status} if app else None

    def get_my_attendance(self, obj):
        user = self._user()
        if not (user and user.is_authenticated):
            return None
        att = obj.attendance_records.filter(volunteer=user).first()
        if not att:
            return None
        hours = getattr(att, "hours_record", None)
        from attendance.models import Feedback

        return {
            "status": att.status,
            "check_in": att.check_in,
            "check_out": att.check_out,
            "hours": float(hours.hours) if hours else None,
            "hours_verified": bool(hours and hours.verified),
            "feedback_submitted": Feedback.objects.filter(event=obj, volunteer=user).exists(),
            "certificate_id": obj.certificates.filter(volunteer=user).values_list("certificate_id", flat=True).first(),
        }

    def get_can_manage(self, obj):
        return can_manage_event(self._user(), obj)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get("can_manage"):
            data.pop("review_note", None)
            data.pop("organizer_notes", None)
        return data


class EventWriteSerializer(serializers.ModelSerializer):
    required_skills = SkillListField(required=False)
    theme = serializers.ChoiceField(choices=EventTheme.choices, required=False)
    contact_phone = serializers.CharField(max_length=20, required=False, allow_blank=True, validators=[validate_phone])

    class Meta:
        model = Event
        fields = [
            "title", "description", "category", "theme", "date", "start_time", "end_time", "location", "latitude",
            "longitude", "maximum_volunteers", "required_skills", "requirements", "meeting_point", "contact_email",
            "contact_phone", "event_image", "instructions", "ngo", "nss_unit",
        ]
        extra_kwargs = {"ngo": {"required": False}, "nss_unit": {"required": False}}

    def validate_date(self, value):
        if self.instance is None and value < timezone.localdate():
            raise serializers.ValidationError("Event date cannot be in the past.")
        return value

    def validate_maximum_volunteers(self, value):
        if value < 1 or value > 5000:
            raise serializers.ValidationError("Must be between 1 and 5000.")
        return value

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start == end:
            raise serializers.ValidationError({"end_time": "End time must differ from start time."})
        if start and end and end < start and (datetime.datetime.combine(datetime.date.today(), end) + datetime.timedelta(days=1)
                                               - datetime.datetime.combine(datetime.date.today(), start)).seconds > 12 * 3600:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        lat, lng = attrs.get("latitude"), attrs.get("longitude")
        if lat is not None and not -90 <= lat <= 90:
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if lng is not None and not -180 <= lng <= 180:
            raise serializers.ValidationError({"longitude": "Longitude must be between -180 and 180."})
        if self.instance is not None and "maximum_volunteers" in attrs:
            approved = self.instance.applications.filter(status__in=[ApplicationStatus.APPROVED, ApplicationStatus.COMPLETED]).count()
            if attrs["maximum_volunteers"] < approved:
                raise serializers.ValidationError({"maximum_volunteers": f"{approved} volunteers are already approved."})
        return attrs

    def _save_skills(self, event, names):
        if names is not None:
            event.required_skills.set(skills_from_names(names))

    def create(self, validated_data):
        names = validated_data.pop("required_skills", None)
        event = Event.objects.create(**validated_data)
        self._save_skills(event, names)
        return event

    def update(self, instance, validated_data):
        names = validated_data.pop("required_skills", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        self._save_skills(instance, names)
        return instance


class ApplicationSerializer(serializers.ModelSerializer):
    volunteer_name = serializers.CharField(source="volunteer.display_name", read_only=True)
    volunteer_gender = serializers.CharField(source="volunteer.gender", read_only=True)
    event_title = serializers.CharField(source="event.title", read_only=True)
    event_date = serializers.DateField(source="event.date", read_only=True)
    event_category = serializers.CharField(source="event.category", read_only=True)
    event_status = serializers.CharField(source="event.status", read_only=True)
    college_name = serializers.CharField(source="college.name", read_only=True, default=None)
    nss_unit_name = serializers.SerializerMethodField()
    skills = SkillListField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    attendance_status = serializers.SerializerMethodField()

    class Meta:
        model = EventApplication
        fields = [
            "id", "volunteer", "volunteer_name", "volunteer_gender", "event", "event_title", "event_date", "event_category",
            "event_status", "college", "college_name", "nss_unit", "nss_unit_name", "email", "phone", "skills", "motivation",
            "application_date", "status", "status_display", "decided_at", "attendance_status",
        ]
        read_only_fields = fields

    def get_nss_unit_name(self, obj):
        return str(obj.nss_unit) if obj.nss_unit_id else None

    def get_attendance_status(self, obj):
        rec = obj.attendance_records.first() if hasattr(obj, "attendance_records") else None
        return rec.status if rec else None


class RegisterForEventSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, validators=[validate_phone])
    email = serializers.EmailField(required=False)
    skills = SkillListField(required=False)
    motivation = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class GroupApplicationSerializer(serializers.ModelSerializer):
    nss_unit_name = serializers.CharField(source="nss_unit.__str__", read_only=True)
    event_title = serializers.CharField(source="event.title", read_only=True)
    skills = SkillListField(required=False)
    submitted_by_name = serializers.CharField(source="submitted_by.display_name", read_only=True, default=None)

    class Meta:
        model = GroupApplication
        fields = [
            "id", "nss_unit", "nss_unit_name", "event", "event_title", "requested_volunteer_count", "skills",
            "message", "status", "submitted_by_name", "decided_at", "created_at",
        ]
        read_only_fields = ["event", "status", "decided_at", "created_at"]


class EventPhotoSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.display_name", read_only=True, default=None)
    # Accepted as plain input fields (not required) so the frontend can send the
    # browser's Geolocation coordinates alongside the file; EXIF is only tried as
    # a fallback in the view if these come through empty. See EventViewSet.photos.
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)

    class Meta:
        model = EventPhoto
        fields = [
            "id", "event", "photo", "caption", "uploaded_by", "uploaded_by_name", "created_at",
            "latitude", "longitude", "location_source",
        ]
        read_only_fields = ["event", "uploaded_by", "created_at", "location_source"]


class EmergencyRequestSerializer(serializers.ModelSerializer):
    required_skills = SkillListField(required=False)
    event_title = serializers.CharField(source="event.title", read_only=True, default=None)
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True, default=None)
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = EmergencyVolunteerRequest
        fields = [
            "id", "title", "description", "event", "event_title", "required_volunteers", "required_skills", "location",
            "latitude", "longitude", "priority", "notified_count", "created_by_name", "created_at", "expires_at", "is_active",
        ]
        read_only_fields = ["notified_count", "created_at"]

    def get_is_active(self, obj):
        return obj.expires_at > timezone.now()

    def validate_expires_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Expiry must be in the future.")
        return value

    def create(self, validated_data):
        names = validated_data.pop("required_skills", None)
        obj = super().create(validated_data)
        if names:
            obj.required_skills.set(skills_from_names(names))
        return obj
