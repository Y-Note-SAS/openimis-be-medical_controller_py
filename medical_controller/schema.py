from graphene_django import DjangoObjectType
import graphene
from core.schema import OrderedDjangoFilterConnectionField
from .models import MissionHealthFacility, MedicalControlMission
from django.db.models import Q
import graphene_django_optimizer as gql_optimizer
from .apps import MedicalControllerConfig
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from core import prefix_filterset, ExtendedConnection
from location.schema import HealthFacilityGQLType, LocationGQLType
from core.schema import UserGQLType
from core.models import User
from.gql_mutations import CreateMissionMutation, UpdateMissionMutation
from django.contrib.auth import get_user_model

class MissionGQLType(DjangoObjectType):

    client_mutation_id = graphene.String()

    class Meta:
        model = MedicalControlMission
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "mission_code": ["exact", "istartswith", "icontains", "iexact"],
            "status": ["exact", "gt"],
            "start_date": ["exact", "lt", "lte", "gt", "gte"],
            "end_date": ["exact", "lt", "lte", "gt", "gte"],
            **prefix_filterset("region__", LocationGQLType._meta.filter_fields),
            **prefix_filterset("district__", LocationGQLType._meta.filter_fields),
            **prefix_filterset("user__", UserGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection


class MissionHFGQLType(DjangoObjectType):

    client_mutation_id = graphene.String()

    class Meta:
        model = MissionHealthFacility
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            **prefix_filterset("mission__", MissionGQLType._meta.filter_fields),
            **prefix_filterset("health_facility__", HealthFacilityGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection


class Query(graphene.ObjectType):

    missions = OrderedDjangoFilterConnectionField(
        MissionGQLType,
        orderBy=graphene.List(of_type=graphene.String),
        category=graphene.String(),
        percentage=graphene.String()
    )

    medical_controllers = OrderedDjangoFilterConnectionField(
        UserGQLType
    )

    def resolve_medical_controllers(self, info, search=None, **kwargs):
        if not info.context.user.has_perms(
            MedicalControllerConfig.gql_mutation_medical_controller_perms):
            raise PermissionDenied(_("unauthorized"))

        return User.objects.filter(
            validity_to__isnull=True,
            i_user__user_roles__role__rights__right_id=112000
        ).distinct()


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
                mission_code=mission_code
            ))

        if filters:
            query = query.filter(*filters)

        return gql_optimizer.query(query, info)

class Mutation(graphene.ObjectType):
    create_mission = CreateMissionMutation.Field()
    update_mission = UpdateMissionMutation.Field()
