from rest_framework import serializers

from .models import NGO, VerificationDocument

FOCUS_AREAS = {"ENVIRONMENT", "COMMUNITY", "HEALTH", "EDUCATION", "AWARENESS", "OTHER"}


class NGOSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    event_count = serializers.IntegerField(read_only=True, required=False)
    upcoming_event_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = NGO
        fields = [
            "id", "name", "description", "logo", "location", "latitude", "longitude", "focus_areas", "email", "phone",
            "website", "registration_number", "verified", "verification_status", "verified_at", "review_note",
            "owner", "owner_name", "event_count", "upcoming_event_count", "created_at", "updated_at",
        ]
        read_only_fields = ["verified", "verification_status", "verified_at", "review_note", "owner", "created_at", "updated_at"]

    def get_owner_name(self, obj):
        return obj.owner.display_name if obj.owner_id else None

    def to_internal_value(self, data):
        # multipart forms send focus_areas as "A,B" – normalise to a list
        if hasattr(data, "getlist") and "focus_areas" in data:
            data = data.copy()
            raw = data.getlist("focus_areas")
            if len(raw) == 1 and "," in raw[0]:
                raw = raw[0].split(",")
            data = {k: data.get(k) for k in data.keys()}
            data["focus_areas"] = [r.strip() for r in raw if r.strip()]
        return super().to_internal_value(data)

    def validate_focus_areas(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list.")
        bad = [v for v in value if v not in FOCUS_AREAS]
        if bad:
            raise serializers.ValidationError(f"Unknown focus area(s): {', '.join(bad)}")
        return value

    def validate(self, attrs):
        lat, lng = attrs.get("latitude"), attrs.get("longitude")
        if lat is not None and not -90 <= lat <= 90:
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if lng is not None and not -180 <= lng <= 180:
            raise serializers.ValidationError({"longitude": "Longitude must be between -180 and 180."})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        # Private review details only for the owner/admins
        from core.permissions import is_admin

        if not (user and user.is_authenticated and (instance.owner_id == user.id or is_admin(user))):
            data.pop("review_note", None)
            data.pop("registration_number", None)
        return data


class VerificationDocumentSerializer(serializers.ModelSerializer):
    reviewed_by_name = serializers.SerializerMethodField()
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)
    file = serializers.FileField(write_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = VerificationDocument
        fields = [
            "id", "ngo", "document_type", "document_type_display", "file", "download_url", "original_filename", "status",
            "uploaded_at", "reviewed_at", "reviewed_by", "reviewed_by_name", "review_note",
        ]
        read_only_fields = ["ngo", "original_filename", "status", "uploaded_at", "reviewed_at", "reviewed_by", "review_note"]

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.display_name if obj.reviewed_by_id else None

    def get_download_url(self, obj):
        return f"/api/documents/{obj.id}/download/"

    def validate_file(self, f):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from core.validators import validate_document_file

        try:
            validate_document_file(f)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return f
