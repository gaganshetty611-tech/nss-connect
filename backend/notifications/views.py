from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        unread = self.request.query_params.get("unread")
        if unread in ("1", "true"):
            qs = qs.filter(read=False)
        ntype = self.request.query_params.get("type")
        if ntype:
            qs = qs.filter(notification_type=ntype)
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["unread_count"] = Notification.objects.filter(recipient=request.user, read=False).count()
        return response


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.read = True
    notification.save(update_fields=["read"])
    return Response(NotificationSerializer(notification).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_all_read(request):
    updated = Notification.objects.filter(recipient=request.user, read=False).update(read=True)
    return Response({"updated": updated})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def unread_count(request):
    return Response({"unread_count": Notification.objects.filter(recipient=request.user, read=False).count()})
