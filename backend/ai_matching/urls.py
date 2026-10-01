from django.urls import path

from . import views

urlpatterns = [
    path("events/<int:pk>/recommendations/", views.event_recommendations, name="event-recommendations"),
    path("events/<int:pk>/turnout-estimate/", views.turnout_estimate, name="event-turnout"),
    path("events/<int:pk>/summary/", views.generate_summary, name="event-summary"),
    path("ai/categorize/", views.categorize, name="ai-categorize"),
    path("ai/suggest-datetime/", views.suggest_datetime, name="ai-suggest-datetime"),
]
