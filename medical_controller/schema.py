from graphene_django import DjangoObjectType
import graphene
from core.schema import OrderedDjangoFilterConnectionField
from .models import MissionHealthFacility, MedicalControlMission
from django.db.models import Q
import graphene_django_optimizer as gql_optimizer
from .apps import MedicalControllerConfig
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

class MissionHFGQLType(DjangoObjectType):

    class Meta:
        model = MissionHealthFacility

class MissionGQLType(DjangoObjectType):

    class Meta:
        model = MedicalControlMission

class Query(graphene.ObjectType):

    missions = OrderedDjangoFilterConnectionField(
        MissionGQLType,
        region_id=graphene.Int(),
        district_id=graphene.Int(),
        status=graphene.String(),
        mission_code=graphene.String(),
        start_date=graphene.Date(),
        end_date=graphene.Date(),
        category=graphene.String(),
        percentage=graphene.String()
    )

    mission = graphene.Field(
        MissionGQLType,
        id=graphene.Int(),
        uuid=graphene.UUID()
    )

def resolve_mission(self, info, **kwargs):
    if (
        not info.context.user.has_perms(
            MedicalControllerConfig.gql_mutation_medical_controller_perms
        )
    ):
        raise PermissionDenied(_("unauthorized"))

    if kwargs.get("id"):
        return MedicalControlMission.objects.get(
            id=kwargs["id"]
        )

    if kwargs.get("uuid"):
        return MedicalControlMission.objects.get(
            uuid=kwargs["uuid"]
        )

    return None

def resolve_missions(self, info, **kwargs):
    if (
        not info.context.user.has_perms(
            MedicalControllerConfig.gql_mutation_medical_controller_perms
        )
    ):
        raise PermissionDenied(_("unauthorized"))

    query = MedicalControlMission.objects.all()

    filters = []

    region_id = kwargs.get("region_id")
    district_id = kwargs.get("district_id")
    status = kwargs.get("status")
    mission_code = kwargs.get("mission_code")

    if region_id:
        filters.append(Q(region_id=region_id))

    if district_id:
        filters.append(Q(district_id=district_id))

    if status:
        filters.append(Q(status=status))

    if mission_code:
        filters.append(Q(
            mission_code__icontains=mission_code
        ))

    if filters:
        query = query.filter(*filters)

    return gql_optimizer.query(query, info)
