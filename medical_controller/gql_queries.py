import graphene
from core import prefix_filterset, ExtendedConnection
from location.schema import HealthFacilityGQLType, LocationGQLType
from claim.gql_queries import ClaimGQLType
from graphene_django import DjangoObjectType
from core.schema import UserGQLType
from .models import MedicalControlMission, MissionHealthFacility, FilteredClaimsForMission


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


class FilteredClaimsForMissionGQLType(DjangoObjectType):

    client_mutation_id = graphene.String()


    class Meta:
        model = FilteredClaimsForMission
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            **prefix_filterset("claim__", ClaimGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection
