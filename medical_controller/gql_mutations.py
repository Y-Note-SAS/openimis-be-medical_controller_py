import graphene
from core.schema import OpenIMISMutation
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from location.models import Location
from .models import MedicalControlMission, MissionHealthFacility
from core.gql.gql_mutations.base_mutation import (
    BaseHistoryModelDeleteMutationMixin,
    BaseUpdateMutationMixin
)
from django.utils.translation import gettext as _
from .apps import MedicalControllerConfig
from django.core.exceptions import PermissionDenied
from core import TimeUtils

class CreateMissionInputType(OpenIMISMutation.Input):

    region_id = graphene.Int(required=True)

    district_id = graphene.Int(required=True)

    health_facility_ids = graphene.List(
        graphene.Int,
        required=True
    )

    start_date = graphene.Date(required=True)

    end_date = graphene.Date(required=True)

    status = graphene.Int(required=False)


def generate_mission_code(region):
    prefix = str(region.code)

    last = (
        MedicalControlMission.objects
        .filter(region=region)
        .order_by("-id")
        .first()
    )

    if not last:
        seq = 1
    else:
        seq = int(last.mission_code[len(prefix):]) + 1

    return f"{prefix}{seq:05d}"

class CreateMissionMutation(BaseHistoryModelDeleteMutationMixin, BaseUpdateMutationMixin):

    _mutation_module = "medical_control"

    _mutation_class = "CreateMissionMutation"
    _model = MedicalControlMission

    @classmethod
    def _validate_mutation(cls, user, **data):
        if type(user) is AnonymousUser or not user.id:
            raise ValidationError("mutation.authentication_required")
        if not user.has_perms(
                MedicalControllerConfig.gql_mutation_medical_controller_perms):
            raise PermissionDenied(_("unauthorized"))

    class Input(CreateMissionInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):

        if type(user) is AnonymousUser or not user.id:
            raise ValidationError(
                _("mutation.authentication_required")
            )

        data["user_created"] = user.id_for_audit
        data["date_created"] = TimeUtils.now()

        if "client_mutation_id" in data:
            data.pop("client_mutation_id")
        if "client_mutation_label" in data:
            data.pop("client_mutation_label")

        region = Location.objects.get(
            pk=data["region_id"]
        )

        district = Location.objects.get(
            pk=data["district_id"]
        )

        hf_ids = data["health_facility_ids"]

        if not hf_ids:
            raise ValidationError(
                _("At least one health facility is required")
            )

        if data["end_date"] <= data["start_date"]:
            raise ValidationError(
                _("End date must be greater than start date")
            )

        mission = MedicalControlMission.objects.create(
            mission_code=generate_mission_code(region),
            region=region,
            district=district,
            start_date=data["start_date"],
            end_date=data["end_date"],
            status=MedicalControlMission.STATUS_IN_PROGRESS,
            user=user._u,
            audit_user_id=user.id_for_audit
        )

        MissionHealthFacility.objects.bulk_create([
            MissionHealthFacility(
                mission=mission,
                health_facility_id=hf_id,
                audit_user_id=user.id_for_audit
            )
            for hf_id in hf_ids
        ])

        return {
            "mission_code": mission.mission_code
        }
