from django.db import models

from core import models as core_models
from location.models import Location
from location.models import HealthFacility
from core.models import User
from claim.models import Claim
from django.utils import timezone as django_tz


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

    percentage_one = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        db_column='PercentageOne'
    )

    percentage_two = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        db_column='PercentageTwo'
    )

    percentage_three = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        db_column='PercentageThree'
    )

    percentage_four = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        db_column='PercentageFour'
    )

    class Meta:
        db_table = "tblMedicalControlMission"


class FilteredClaimsForMission(core_models.HistoryModel):

    mission = models.ForeignKey(
        MedicalControlMission,
        on_delete=models.DO_NOTHING,
        related_name="mission_health_facilities"
    )

    claim = models.ForeignKey(
        Claim,
        on_delete=models.DO_NOTHING
    )

    from_rejected_to_valuated = models.BooleanField(
        db_column='RejectedToValuated',
        blank=True,
        null=True
    )

    audit_explanation = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        db_column='AuditExplanation'
    )

    audited = models.BooleanField(
        db_column='Audited',
        blank=True,
        null=True
    )

    claim_category = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        db_column='ClaimCategory'
    )

    class Meta:
        db_table = "tblFilteredClaimsForMission"


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


class MissionActivityHistory(core_models.HistoryModel):

    mission = models.ForeignKey(
        MedicalControlMission,
        on_delete=models.DO_NOTHING,
        related_name="activity_mission_hf"
    )

    action = models.TextField(
        blank=True,
        null=True,
        db_column='Action'
    )

    action_date = models.DateTimeField(
        blank=True,
        null=True,
        db_column='ActionDate',
        default=django_tz.now
    )

    user = models.ForeignKey(
        User,
        db_column='userID',
        on_delete=models.DO_NOTHING
    )

    class Meta:
        db_table = "tblMissionActivityHistory"

def medical_controller_claims_report_query():
    return []
