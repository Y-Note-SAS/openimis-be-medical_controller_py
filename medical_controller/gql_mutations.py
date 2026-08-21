import graphene
from core.schema import OpenIMISMutation
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from location.models import Location
from .models import MedicalControlMission, MissionHealthFacility
from django.utils.translation import gettext as _
from .apps import MedicalControllerConfig
from django.core.exceptions import PermissionDenied
from core import TimeUtils
import uuid

class CreateMissionInputType(OpenIMISMutation.Input):

    region_id = graphene.Int(required=True)

    district_id = graphene.Int(required=True)

    health_facility_ids = graphene.List(
        graphene.Int,
        required=True
    )

    start_date = graphene.Date(required=True)

    end_date = graphene.Date(required=True)

    status = graphene.String(required=False)


class UpdateMissionInputType(OpenIMISMutation.Input):

    status = graphene.String(required=True)
    mission_code = graphene.String(required=True)

def generate_mission_code(region):
    prefix = str(region.code)

    last = (
        MedicalControlMission.objects
        .filter(region=region)
        .order_by("-mission_code")
        .first()
    )

    if not last:
        seq = 1
    else:
        seq = int(last.mission_code[len(prefix):]) + 1

    return f"{prefix}{seq:05d}"


class CreateMissionMutation(OpenIMISMutation):

    _mutation_module = "medical_controller"

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

        mission = MedicalControlMission(
            mission_code=generate_mission_code(region),
            region=region,
            district=district,
            start_date=data["start_date"],
            end_date=data["end_date"],
            status=MedicalControlMission.STATUS_IN_PROGRESS,
            user=user
        )
        mission.save(username=user.username)

        MissionHealthFacility.objects.bulk_create([
            MissionHealthFacility(
                id=uuid.uuid4(),
                mission=mission,
                user_created=user,
                user_updated=user,
                health_facility_id=hf_id
            )
            for hf_id in hf_ids
        ])


class UpdateMissionMutation(OpenIMISMutation):

    _mutation_module = "medical_controller"

    _mutation_class = "UpdateMissionMutation"
    _model = MedicalControlMission

    @classmethod
    def _validate_mutation(cls, user, **data):
        if type(user) is AnonymousUser or not user.id:
            raise ValidationError("mutation.authentication_required")
        if not user.has_perms(
                MedicalControllerConfig.gql_mutation_medical_controller_perms):
            raise PermissionDenied(_("unauthorized"))

    class Input(UpdateMissionInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):

        if type(user) is AnonymousUser or not user.id:
            raise ValidationError(
                _("mutation.authentication_required")
            )

        mission_code = data.get("mission_code", None)
        mission_status = data.get("status", None)
        if not mission_code:
            raise ValidationError(
                _("mutation.no_mission_code_sent_for_update")
            )

        if not mission_status:
            raise ValidationError(
                _("mutation.no_mission_status")
            )

        if "client_mutation_id" in data:
            data.pop("client_mutation_id")
        if "client_mutation_label" in data:
            data.pop("client_mutation_label")

        mission = (
            MedicalControlMission.objects
            .get(
                mission_code=mission_code
            )
        )
        mission.status = mission_status
        mission.user_updated = user
        mission.date_updated = TimeUtils.now()
        mission.save(username=user.username)
