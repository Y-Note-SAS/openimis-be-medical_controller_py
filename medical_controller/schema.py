import graphene
from core.schema import OrderedDjangoFilterConnectionField
from .apps import MedicalControllerConfig
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from core.schema import UserGQLType
from claim.gql_queries import ClaimGQLType
from core.models import User
from.gql_mutations import CreateMissionMutation, UpdateMissionMutation
from .gql_queries import MissionGQLType, FilteredClaimsForMissionGQLType, MissionActivityHistoryGQLType
from .models import MedicalControlMission, FilteredClaimsForMission, MissionActivityHistory
from claim.models import Claim
from .services import process_category
from django.core.exceptions import ValidationError
import graphene_django_optimizer as gql_optimizer


class ClaimsForHealthFacilitiesResultGQLType(graphene.ObjectType):

    total_categ1 = graphene.String()
    total_categ2 = graphene.String()
    total_categ3 = graphene.String()
    total_categ4 = graphene.String()

    percentage_categ1 = graphene.String()
    percentage_categ2 = graphene.String()
    percentage_categ3 = graphene.String()
    percentage_categ4 = graphene.String()

    claims = OrderedDjangoFilterConnectionField(
        FilteredClaimsForMissionGQLType
    )


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


class Query(graphene.ObjectType):

    missions = OrderedDjangoFilterConnectionField(
        MissionGQLType,
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
        category=graphene.String(required=False)
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
            MedicalControllerConfig.gql_mutation_medical_controller_perms):
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
        category = kwargs.get("category", None)
        if category:
            base_query = base_query.filter(claim_category=category)

        ids = base_query.values_list("id", flat=True).distinct()

        query = FilteredClaimsForMission.objects.filter(id__in=ids)
        claims = query

        return ClaimsForHealthFacilitiesResultGQLType(

            total_categ1=
            FilteredClaimsForMission.objects.filter(
                mission=mission,
                claim_category="1",
            ).count(),

            total_categ2=
            FilteredClaimsForMission.objects.filter(
                mission=mission,
                claim_category="2",
            ).count(),

            total_categ3=
            FilteredClaimsForMission.objects.filter(
                mission=mission,
                claim_category="3",
            ).count(),

            total_categ4=
            FilteredClaimsForMission.objects.filter(
                mission=mission,
                claim_category="4",
            ).count(),

            percentage_categ1=
            mission.percentage_one,

            percentage_categ2=
            mission.percentage_two,

            percentage_categ3=
            mission.percentage_three,

            percentage_categ4=
            mission.percentage_four,

            claims=claims,
        )

    def resolve_mission_activity_history(self, info, search=None, **kwargs):
        if not info.context.user.has_perms(
            MedicalControllerConfig.gql_mutation_medical_controller_perms):
            raise PermissionDenied(_("unauthorized"))

        mission_code = kwargs.get(
            "mission_code"
        )
        mission = MedicalControlMission.objects.filter(mission_code=mission_code).first()
        if not mission:
            raise ValidationError(_("mutation.mission.not.exist"))

        query = FilteredClaimsForMission.objects.filter(mission=mission)

        return gql_optimizer.query(query, info)

    def resolve_medical_controllers(self, info, search=None, **kwargs):
        if not info.context.user.has_perms(
            MedicalControllerConfig.gql_mutation_medical_controller_perms):
            raise PermissionDenied(_("unauthorized"))

        return User.objects.filter(
            validity_to__isnull=True,
            i_user__user_roles__role__rights__right_id=112000
        ).distinct()

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

        category_one_claims = process_category(
            mission=mission,
            category="1",
            percentage=percentage_categ_one,
            health_facilities=health_facilities,
            user=info.context.user
        )
        print("category_one_claims ", category_one_claims)

        category_two_claims = process_category(
            mission=mission,
            category="2",
            percentage=percentage_categ_two,
            health_facilities=health_facilities,
            user=info.context.user
        )
        print("category_two_claims ", category_two_claims)

        category_three_claims = process_category(
            mission=mission,
            category="3",
            percentage=percentage_categ_three,
            health_facilities=health_facilities,
            user=info.context.user
        )
        print("category_three_claims ", category_three_claims)

        category_four_claims = process_category(
            mission=mission,
            category="4",
            percentage=percentage_categ_four,
            health_facilities=health_facilities,
            user=info.context.user
        )
        print("category_four_claims ", category_four_claims)

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
