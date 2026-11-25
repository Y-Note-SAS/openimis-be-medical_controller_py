import uuid
import graphene
from core import TimeUtils
from core.schema import OpenIMISMutation
from claim.models import Claim
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from location.models import Location
from .models import (
    MedicalControlMission,
    MissionHealthFacility,
    MissionActivityHistory,
    FilteredClaimsForMission,
    MissionUsers,
    MissionDistricts
)

from .apps import MedicalControllerConfig


def _clean_mission_user_ids(user, user_ids):
    """Retire le chef de mission et les doublons des auditeurs.

    Le chef de mission est le createur de la mission : il ne peut pas etre
    enregistre comme auditeur de sa propre mission, quelle que soit l'interface
    appelante.
    """
    chief_id = None
    i_user = getattr(user, "i_user", None)
    if i_user is not None:
        chief_id = getattr(i_user, "id", None)

    cleaned = []
    for user_id in user_ids or []:
        if user_id is None or user_id == chief_id or user_id in cleaned:
            continue
        cleaned.append(user_id)
    return cleaned


class CreateMissionInputType(OpenIMISMutation.Input):

    region_id = graphene.Int(required=True)

    health_facility_ids = graphene.List(
        graphene.Int,
        required=True
    )

    user_ids = graphene.List(
        graphene.Int,
        required=False
    )

    district_ids = graphene.List(
        graphene.Int,
        required=True
    )

    start_date = graphene.Date(required=True)

    end_date = graphene.Date(required=True)

    mission_date = graphene.Date(required=True)

    status = graphene.String(required=False)


class UpdateMissionInputType(OpenIMISMutation.Input):

    status = graphene.String(required=True)
    mission_code = graphene.String(required=True)
    user_ids = graphene.List(
        graphene.Int,
        required=False
    )


class TreatClaimsInBlockInputType(OpenIMISMutation.Input):

    action = graphene.String(required=True)
    claim_ids = graphene.List(
        graphene.Int,
        required=False
    )


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
        if type(user) is AnonymousUser or not user or not user.id:
            raise ValidationError("mutation.authentication_required")
        if not user.has_perms(
                MedicalControllerConfig.gql_mutation_medical_controller_perms):
            raise PermissionDenied(_("unauthorized"))

    class Input(CreateMissionInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):

        if type(user) is AnonymousUser or not user or not user.id:
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

        hf_ids = data["health_facility_ids"]

        user_ids = _clean_mission_user_ids(user, data.get("user_ids", []))

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
            start_date=data["start_date"],
            end_date=data["end_date"],
            mission_date=data["mission_date"],
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

        if user_ids:
            MissionUsers.objects.bulk_create([
                MissionUsers(
                    id=uuid.uuid4(),
                    mission=mission,
                    user_created=user,
                    user_updated=user,
                    user_id=user_id
                )
                for user_id in user_ids
            ])

        district_ids = data.get("district_ids", [])

        MissionDistricts.objects.bulk_create([
            MissionDistricts(
                id=uuid.uuid4(),
                mission=mission,
                user_created=user,
                user_updated=user,
                district_id=district_id
            )
            for district_id in district_ids
        ])

        msg = _("Created mission %(mission_code)s") % {
            "mission_code": mission.mission_code,
        }
        mission_activity = MissionActivityHistory(
            mission=mission,
            action=msg,
            user=user,
            user_created=user,
            user_updated=user,
        )
        mission_activity.save(username=user.username)


class TreatClaimsMutation(OpenIMISMutation):

    _mutation_module = "medical_controller"

    _mutation_class = "TreatClaimsMutation"
    _model = MedicalControlMission

    @classmethod
    def _validate_mutation(cls, user, **data):
        if type(user) is AnonymousUser or not user or not user.id:
            raise ValidationError("mutation.authentication_required")
        if not user.has_perms(
                MedicalControllerConfig.gql_mutation_medical_controller_perms):
            raise PermissionDenied(_("unauthorized"))

    class Input(TreatClaimsInBlockInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):

        if type(user) is AnonymousUser or not user or not user.id:
            raise ValidationError(
                _("mutation.authentication_required")
            )

        action = data.get("action", None)
        claim_ids = data.get("claim_ids", [])
        if not action:
            raise ValidationError(
                _("mutation.no_action_sent_for_treat_claims")
            )
        if not claim_ids:
            raise ValidationError(
                _("mutation.no_claim_ids_sent_for_treat_claims")
            )
        if action not in ["adopt", "rehabilitate"]:
            raise ValidationError(
                _("mutation.action_must_be_adopt_or_rehabilitate")
            )

        if action == "adopt":
            Claim.objects.filter(
                id__in=claim_ids, validity_to__isnull=True).update(audit_status='A')

        if action == "rehabilitate":
            # Ensure all claims are in rejected status before rehabilitation
            non_rejected = Claim.objects.filter(
                id__in=claim_ids, validity_to__isnull=True).exclude(status=1)
            if non_rejected.exists():
                c = list(non_rejected.values_list('code', flat=True))
                raise ValidationError(
                    f"Cannot rehabilitate: the following claims are not rejected: {', '.join(c)}"
                )
            Claim.objects.filter(
                id__in=claim_ids, validity_to__isnull=True).update(audit_status='H')


class UpdateMissionMutation(OpenIMISMutation):

    _mutation_module = "medical_controller"

    _mutation_class = "UpdateMissionMutation"
    _model = MedicalControlMission

    @classmethod
    def _validate_mutation(cls, user, **data):
        if type(user) is AnonymousUser or not user or not user.id:
            raise ValidationError("mutation.authentication_required")
        if not user.has_perms(
                MedicalControllerConfig.gql_mutation_medical_controller_perms):
            raise PermissionDenied(_("unauthorized"))

    class Input(UpdateMissionInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):

        if type(user) is AnonymousUser or not user or not user.id:
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

        if mission_status == "C":
            if user.id != mission.user_created.id:
                raise ValidationError(
                    _("mutation.only_mission_chief_can_close_mission")
                )

        user_ids = _clean_mission_user_ids(user, data.get("user_ids", []))
        MissionUsers.objects.filter(mission=mission).delete()
        MissionUsers.objects.bulk_create([
            MissionUsers(
                id=uuid.uuid4(),
                mission=mission,
                user_created=user,
                user_updated=user,
                user_id=user_id
            )
            for user_id in user_ids
        ])
        msg = _("Set controllers to %(user_ids)s on the mission %(mission_code)s") % {
            "user_ids": user_ids,
            "mission_code": mission.mission_code
        }

        if mission_status == "C":
            claims_for_mission = FilteredClaimsForMission.objects.filter(
                mission=mission
            ).all()
            for missionclaim in claims_for_mission:
                if not missionclaim.claim.audited:
                    return [
                        {
                            'message': _("mutation.all_claims_not_audited"),
                            'detail': _("You must audit all claims before closing the mission")
                        }
                    ]
        if mission.status != mission_status:
            types = {
                "C": _("Closed"),
                "P": _("In progess")
            }
            status = types.get(mission_status)

            mission.status = mission_status
            msg += _("Changed mission %(mission_code)s status to %(status)s") % {
                "mission_code": mission.mission_code,
                "status": status
            }
        mission.user_updated = user
        mission.date_updated = TimeUtils.now()
        mission.save(username=user.username)

        mission_activity = MissionActivityHistory(
            mission=mission,
            action=msg,
            user=user,
            user_created=user,
            user_updated=user,
        )
        mission_activity.save(username=user.username)
