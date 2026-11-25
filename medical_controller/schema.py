import graphene
import graphene_django_optimizer as gql_optimizer

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.utils.translation import gettext as _

from claim.gql_queries import ClaimGQLType
from claim.models import Claim
from core.models import User
from core.schema import OrderedDjangoFilterConnectionField, UserGQLType

from location.models import HealthFacility
from .apps import MedicalControllerConfig
from .gql_mutations import (
    CreateMissionMutation,
    UpdateMissionMutation,
    TreatClaimsMutation
)
from .gql_queries import (
    FilteredClaimsForMissionGQLType,
    MissionActivityHistoryGQLType,
    MissionGQLType,
    MissionDistrictGQLType,
    MissionUserGQLType
)
from .models import (
    FilteredClaimsForMission,
    MedicalControlMission,
    MissionActivityHistory,
    MissionDistricts,
    MissionHealthFacility
)
from .services import process_category


class ClaimsForHealthFacilitiesResultGQLType(graphene.ObjectType):

    total_categ1 = graphene.String()
    total_categ2 = graphene.String()
    total_categ3 = graphene.String()
    total_categ4 = graphene.String()
    total_categ5 = graphene.String()

    percentage_categ1 = graphene.String()
    percentage_categ2 = graphene.String()
    percentage_categ3 = graphene.String()
    percentage_categ4 = graphene.String()
    percentage_categ5 = graphene.String()

    claims = OrderedDjangoFilterConnectionField(
        FilteredClaimsForMissionGQLType,
        orderBy=graphene.List(of_type=graphene.String),
    )

    all_audited = graphene.Boolean()


class DistrictHFGQLType(graphene.ObjectType):
    district_ids = graphene.List(graphene.Int)
    health_facility_ids = graphene.List(graphene.Int)


class ClaimSampleCategoryGQLType(graphene.ObjectType):
    category = graphene.String()
    total_category = graphene.Int()
    audited = graphene.Int()
    claims = graphene.List(ClaimGQLType)
    percentage = graphene.String()


class ClaimSampleResultGQLType(graphene.ObjectType):
    category_one = graphene.Field(
        ClaimSampleCategoryGQLType
    )

    category_two = graphene.Field(
        ClaimSampleCategoryGQLType
    )

    category_three = graphene.Field(
        ClaimSampleCategoryGQLType
    )

    category_four = graphene.Field(
        ClaimSampleCategoryGQLType
    )

    category_five = graphene.Field(
        ClaimSampleCategoryGQLType
    )


class Query(graphene.ObjectType):

    missions = OrderedDjangoFilterConnectionField(
        MissionGQLType,
        orderBy=graphene.List(of_type=graphene.String),
    )

    missions_users = OrderedDjangoFilterConnectionField(
        MissionUserGQLType,
        orderBy=graphene.List(of_type=graphene.String),
    )

    missions_districts = OrderedDjangoFilterConnectionField(
        MissionDistrictGQLType,
        orderBy=graphene.List(of_type=graphene.String),
    )

    medical_controllers = OrderedDjangoFilterConnectionField(
        UserGQLType
    )

    claims_for_health_facilities = graphene.Field(
        ClaimsForHealthFacilitiesResultGQLType,
        health_facility_ids=graphene.List(
            graphene.Int,
            required=True
        ),
        mission_code=graphene.String(required=True),
        category=graphene.String(required=False),
        services=graphene.List(
            graphene.String,
            required=False
        )
    )

    check_mission_availability = graphene.Field(
        DistrictHFGQLType,
        health_facility_ids = graphene.List(graphene.Int, required=True),
        district_ids = graphene.List(graphene.Int, required=True),
        start_date = graphene.Date(required=True),
        end_date = graphene.Date(required=True)
    )

    mission_activity_history = OrderedDjangoFilterConnectionField(
        MissionActivityHistoryGQLType,
        mission_code=graphene.String(required=True)
    )

    get_claims_sample = graphene.Field(
        ClaimSampleResultGQLType,
        percentage_categ_one=graphene.String(
            required=True
        ),
        percentage_categ_two=graphene.String(
            required=True
        ),
        percentage_categ_three=graphene.String(
            required=True
        ),
        percentage_categ_four=graphene.String(
            required=True
        ),
        percentage_categ_five=graphene.String(
            required=True
        ),
        mission_code=graphene.String(
            required=True
        ),
        health_facility_ids=graphene.List(
            graphene.Int,
            required=True
        )
    )

    def resolve_claims_for_health_facilities(self, info, search=None, **kwargs):
        if not info.context.user.has_perms(
            MedicalControllerConfig.gql_mutation_medical_controller_perms
        ):
            raise PermissionDenied(_("unauthorized"))

        health_facilities = kwargs.get(
            "health_facility_ids",
            []
        )
        mission_code = kwargs.get(
            "mission_code"
        )
        mission = MedicalControlMission.objects.filter(mission_code=mission_code).first()
        if not mission:
            raise ValidationError(_("mutation.mission.not.exist"))

        # 1. Filtrer sans distinct, puis appliquer le filtre catégorie
        base_query = FilteredClaimsForMission.objects.filter(
            claim__health_facility__id__in=health_facilities,
            mission=mission
        )
        all_audited = True
        for mission_claim in base_query:
            if not mission_claim.claim.audited:
                all_audited = False
        category = kwargs.get("category", None)
        if category:
            base_query = base_query.filter(claim_category=category)

        services = kwargs.get("services", None) or []
        if services:
            # le JOIN sur les prestations duplique les lignes -> distinct ci-dessous
            base_query = base_query.filter(
                claim__services__service__code__in=services
            )

        ids = base_query.values_list("id", flat=True).distinct()

        query = FilteredClaimsForMission.objects.filter(id__in=ids)
        # tri par defaut : date de la prestation (date_claimed) croissante,
        # puis claim__id pour une pagination stable
        claims = query.order_by("claim__date_claimed", "claim__id")

        # l'etat d'audit porte sur TOUS les claims de la mission, filtres ignores
        all_audited = not FilteredClaimsForMission.objects.filter(
            mission=mission
        ).filter(
            Q(claim__audited__isnull=True) | Q(claim__audited=False)
        ).exists()

        return ClaimsForHealthFacilitiesResultGQLType(

            total_categ1=FilteredClaimsForMission.objects.filter(
                mission=mission,
                claim_category="1",
            ).count(),

            total_categ2=FilteredClaimsForMission.objects.filter(
                mission=mission,
                claim_category="2",
            ).count(),

            total_categ3=FilteredClaimsForMission.objects.filter(
                mission=mission,
                claim_category="3",
            ).count(),

            total_categ4=FilteredClaimsForMission.objects.filter(
                mission=mission,
                claim_category="4",
            ).count(),

            total_categ5=FilteredClaimsForMission.objects.filter(
                mission=mission,
                claim_category="5",
            ).count(),

            percentage_categ1=mission.percentage_one,

            percentage_categ2=mission.percentage_two,

            percentage_categ3=mission.percentage_three,

            percentage_categ4=mission.percentage_four,

            percentage_categ5=mission.percentage_five,

            claims=claims,

            all_audited=all_audited
        )

    def resolve_mission_activity_history(self, info, search=None, **kwargs):
        if not info.context.user.has_perms(
            MedicalControllerConfig.gql_mutation_medical_controller_perms
        ):
            raise PermissionDenied(_("unauthorized"))

        mission_code = kwargs.get(
            "mission_code"
        )
        mission = MedicalControlMission.objects.filter(mission_code=mission_code).first()
        if not mission:
            raise ValidationError(_("mutation.mission.not.exist"))

        query = MissionActivityHistory.objects.filter(mission=mission)

        return gql_optimizer.query(query, info)

    def resolve_medical_controllers(self, info, search=None, **kwargs):
        if not info.context.user.has_perms(
            MedicalControllerConfig.gql_mutation_medical_controller_perms
        ):
            raise PermissionDenied(_("unauthorized"))

        return User.objects.filter(
            validity_to__isnull=True,
            i_user__user_roles__role__rights__right_id=112000
        ).distinct()

    def resolve_check_mission_availability(
        self,
        info,
        search=None,
        **kwargs,
    ):
        if not info.context.user.has_perms(
            MedicalControllerConfig.gql_mutation_medical_controller_perms
        ):
            raise PermissionDenied(_("unauthorized"))

        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")

        district_ids = kwargs.get("district_ids", [])
        health_facility_ids = kwargs.get("health_facility_ids", [])

        missions = MedicalControlMission.objects.filter(
            start_date__lte=end_date,
            end_date__gte=start_date,
        )

        mission_ids = missions.values_list("id", flat=True)

        assigned_district_ids = set(
            MissionDistricts.objects.filter(
                mission_id__in=mission_ids,
                district_id__in=district_ids,
            ).values_list("district_id", flat=True)
        )

        assigned_hf_ids = set(
            MissionHealthFacility.objects.filter(
                mission_id__in=mission_ids,
                health_facility_id__in=health_facility_ids,
            ).values_list("health_facility_id", flat=True)
        )

        available_hf_ids = [
            hf_id
            for hf_id in health_facility_ids
            if hf_id not in assigned_hf_ids
        ]

        # Un district doit avoir au moins une FOSA disponible
        # et ne doit pas être déjà affecté à une mission.
        available_district_ids = []

        available_hfs_by_district = {}

        for hf in HealthFacility.objects.filter(
            id__in=available_hf_ids,
            location_id__in=district_ids,
        ).values("id", "location_id"):

            available_hfs_by_district.setdefault(
                hf["location_id"], []
            ).append(hf["id"])

        for district_id in district_ids:
            if district_id in assigned_district_ids:
                continue

            if available_hfs_by_district.get(district_id):
                available_district_ids.append(district_id)

        # Ne retourner que les FOSA des districts conservés
        available_hf_ids = [
            hf_id
            for district_id in available_district_ids
            for hf_id in available_hfs_by_district.get(district_id, [])
        ]

        return DistrictHFGQLType(
            district_ids=available_district_ids,
            health_facility_ids=available_hf_ids,
        )

    def resolve_get_claims_sample(
        self,
        info,
        search=None,
        **kwargs,
    ):
        if not info.context.user.has_perms(
            MedicalControllerConfig
            .gql_mutation_medical_controller_perms
        ):
            raise PermissionDenied(
                _("unauthorized")
            )

        mission_code = kwargs.get(
            "mission_code"
        )

        mission = (
            MedicalControlMission.objects
            .filter(
                mission_code=mission_code
            ).first()
        )
        if not mission:
            raise ValidationError(
                _("mutation.mission.not.exist")
            )

        health_facilities = kwargs.get(
            "health_facility_ids",
            [],
        )

        percentage_categ_one = int(
            kwargs.get(
                "percentage_categ_one"
            )
        )

        percentage_categ_two = int(
            kwargs.get(
                "percentage_categ_two"
            )
        )

        percentage_categ_three = int(
            kwargs.get(
                "percentage_categ_three"
            )
        )

        percentage_categ_four = int(
            kwargs.get(
                "percentage_categ_four"
            )
        )

        percentage_categ_five = int(
            kwargs.get(
                "percentage_categ_five"
            )
        )

        category_one_claims = process_category(
            mission=mission,
            category="1",
            percentage=percentage_categ_one,
            health_facilities=health_facilities,
            user=info.context.user
        )

        category_two_claims = process_category(
            mission=mission,
            category="2",
            percentage=percentage_categ_two,
            health_facilities=health_facilities,
            user=info.context.user
        )

        category_three_claims = process_category(
            mission=mission,
            category="3",
            percentage=percentage_categ_three,
            health_facilities=health_facilities,
            user=info.context.user
        )

        category_four_claims = process_category(
            mission=mission,
            category="4",
            percentage=percentage_categ_four,
            health_facilities=health_facilities,
            user=info.context.user
        )

        category_five_claims = process_category(
            mission=mission,
            category="5",
            percentage=percentage_categ_five,
            health_facilities=health_facilities,
            user=info.context.user
        )

        msg = _("Added filter %(kwargs)s on mission %(mission_code)s") % {
            "kwargs": str(kwargs),
            "mission_code": mission_code
        }
        mission_activity = MissionActivityHistory(
            mission=mission,
            action=msg,
            user=info.context.user,
            user_created=info.context.user,
            user_updated=info.context.user,
        )
        mission_activity.save(username=info.context.user.username)

        mission.percentage_one = str(percentage_categ_one)
        mission.percentage_two = str(percentage_categ_two)
        mission.percentage_three = str(percentage_categ_three)
        mission.percentage_four = str(percentage_categ_four)
        mission.percentage_five = str(percentage_categ_five)
        if mission.is_dirty(check_relationship=True):
            mission.save(username=info.context.user.username)

        return ClaimSampleResultGQLType(
            category_one=ClaimSampleCategoryGQLType(
                category="1",
                total_category=build_category_result(mission, "1"),
                claims=category_one_claims,
                percentage=percentage_categ_one
            ),
            category_two=ClaimSampleCategoryGQLType(
                category="2",
                total_category=build_category_result(mission, "2"),
                claims=category_two_claims,
                percentage=percentage_categ_two
            ),
            category_three=ClaimSampleCategoryGQLType(
                category="3",
                total_category=build_category_result(mission, "3"),
                claims=category_three_claims,
                percentage=percentage_categ_three
            ),
            category_four=ClaimSampleCategoryGQLType(
                category="4",
                total_category=build_category_result(mission, "4"),
                claims=category_four_claims,
                percentage=percentage_categ_four
            ),
            category_five=ClaimSampleCategoryGQLType(
                category="5",
                total_category=build_category_result(mission, "5"),
                claims=category_five_claims,
                percentage=percentage_categ_five
            )
        )


def build_category_result(
    mission,
    category,
):
    claim_ids = (
        FilteredClaimsForMission.objects
        .filter(
            mission=mission,
            claim_category=category,
        )
        .values_list(
            "claim_id",
            flat=True,
        )
        .distinct()
    )

    selected_claims = Claim.objects.filter(
        id__in=claim_ids
    )
    return selected_claims.count()


class Mutation(graphene.ObjectType):
    create_mission = CreateMissionMutation.Field()
    update_mission = UpdateMissionMutation.Field()
    treat_claims = TreatClaimsMutation.Field()
