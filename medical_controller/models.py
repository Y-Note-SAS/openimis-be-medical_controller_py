from django.db import models

from core import models as core_models
from location.models import Location
from location.models import HealthFacility
from core.models import User

class MedicalControlMission(core_models.HistoryModel):

    STATUS_IN_PROGRESS = "P"
    STATUS_COMPLETED = "C"

    STATUS_CHOICES = (
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed")
    )

    mission_code = models.CharField(
        max_length=20,
        unique=True
    )

    region = models.ForeignKey(
        Location,
        on_delete=models.DO_NOTHING,
        related_name="medical_control_missions"
    )

    district = models.ForeignKey(
        Location,
        on_delete=models.DO_NOTHING,
        related_name="medical_control_district_missions"
    )

    start_date = models.DateField()

    end_date = models.DateField()

    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES,
        default=STATUS_IN_PROGRESS
    )

    user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING
    )

    json_ext = models.JSONField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = "tblMedicalControlMission"


class MissionHealthFacility(core_models.HistoryModel):

    mission = models.ForeignKey(
        MedicalControlMission,
        on_delete=models.DO_NOTHING,
        related_name="health_facilities"
    )

    health_facility = models.ForeignKey(
        HealthFacility,
        on_delete=models.DO_NOTHING
    )

    class Meta:
        db_table = "tblMedicalControlMissionHF"

        unique_together = (
            "mission",
            "health_facility"
        )
