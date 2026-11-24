import graphene
from core import prefix_filterset, ExtendedConnection
from location.schema import HealthFacilityGQLType, LocationGQLType
from claim.gql_queries import ClaimGQLType
from graphene_django import DjangoObjectType
from core.schema import UserGQLType, InteractiveUserGQLType
from .models import (
    MedicalControlMission,
    MissionHealthFacility,
    FilteredClaimsForMission,
    MissionActivityHistory,
    MissionUsers,
    MissionDistricts
)


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
            "mission_date": ["exact", "lt", "lte", "gt", "gte"],
            "districts__district__id": ["exact", "in"],
            **prefix_filterset("region__", LocationGQLType._meta.filter_fields),
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


class MissionUserGQLType(DjangoObjectType):

    client_mutation_id = graphene.String()

    class Meta:
        model = MissionUsers
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            **prefix_filterset("mission__", MissionGQLType._meta.filter_fields),
            **prefix_filterset("user__", InteractiveUserGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection


class MissionDistrictGQLType(DjangoObjectType):

    client_mutation_id = graphene.String()

    class Meta:
        model = MissionDistricts
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            **prefix_filterset("mission__", MissionGQLType._meta.filter_fields),
            **prefix_filterset("district__", LocationGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection


class FilteredClaimsForMissionGQLType(DjangoObjectType):

    client_mutation_id = graphene.String()

    class Meta:
        model = FilteredClaimsForMission
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            **prefix_filterset("claim__", ClaimGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection


class MissionActivityHistoryGQLType(DjangoObjectType):

    client_mutation_id = graphene.String()

    class Meta:
        model = MissionActivityHistory
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            **prefix_filterset("mission__", MissionGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection
