from rest_framework import serializers

from .models import College, NSSUnit, University


class UniversitySerializer(serializers.ModelSerializer):
    college_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = University
        fields = ["id", "name", "short_name", "city", "college_count", "created_at"]


class CollegeSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)

    class Meta:
        model = College
        fields = ["id", "name", "code", "city", "latitude", "longitude", "university", "university_name", "created_at"]


class NSSUnitSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source="college.name", read_only=True)
    university_name = serializers.CharField(source="university.name", read_only=True)
    coordinator_name = serializers.SerializerMethodField()
    display_name = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = NSSUnit
        fields = [
            "id", "display_name", "college", "college_name", "unit_number", "university", "university_name",
            "coordinator", "coordinator_name", "email", "phone", "location", "latitude", "longitude",
            "volunteer_count", "verified", "verification_status", "created_at", "updated_at",
        ]
        read_only_fields = ["university", "coordinator", "volunteer_count", "verified", "verification_status", "created_at", "updated_at"]

    def get_coordinator_name(self, obj):
        return obj.coordinator.display_name if obj.coordinator_id else None

    def validate(self, attrs):
        lat, lng = attrs.get("latitude"), attrs.get("longitude")
        if lat is not None and not -90 <= lat <= 90:
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if lng is not None and not -180 <= lng <= 180:
            raise serializers.ValidationError({"longitude": "Longitude must be between -180 and 180."})
        return attrs
