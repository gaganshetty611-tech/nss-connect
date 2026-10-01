from django.db import models


class AIRecommendation(models.Model):
    """Stored output of the NSS-unit matching engine for one (event, unit) pair.

    Scores are 0–100. `reasons` is a list of human-readable explanations.
    This is a transparent weighted scoring model, not a trained ML model.
    """

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="ai_recommendations")
    nss_unit = models.ForeignKey("nss_units.NSSUnit", on_delete=models.CASCADE, related_name="ai_recommendations")
    match_score = models.DecimalField(max_digits=5, decimal_places=2, db_index=True)
    distance_score = models.DecimalField(max_digits=5, decimal_places=2)
    skill_score = models.DecimalField(max_digits=5, decimal_places=2)
    availability_score = models.DecimalField(max_digits=5, decimal_places=2)
    attendance_score = models.DecimalField(max_digits=5, decimal_places=2)
    interest_score = models.DecimalField(max_digits=5, decimal_places=2)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    available_volunteers = models.PositiveIntegerField(default=0)
    reasons = models.JSONField(default=list)
    provider = models.CharField(max_length=30, default="rule_based")
    weights = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-match_score"]
        constraints = [models.UniqueConstraint(fields=["event", "nss_unit"], name="uniq_recommendation_event_unit")]

    def __str__(self):
        return f"{self.nss_unit} for {self.event}: {self.match_score}"
