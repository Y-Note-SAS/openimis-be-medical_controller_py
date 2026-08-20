import graphene
from core.schema import OrderedDjangoFilterConnectionField
from .apps import MedicalControllerConfig
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from core.schema import UserGQLType
from claim.gql_queries import ClaimGQLType
from core.models import User
from.gql_mutations import CreateMissionMutation, UpdateMissionMutation
from .gql_queries import MissionGQLType
from .models import MedicalControlMission, FilteredClaimsForMission
from claim.models import Claim
from .services import process_category


class ClaimSampleCategoryGQLType(graphene.ObjectType):
    category = graphene.String()
    total_category = graphene.Int()
    audited = graphene.Int()
    claims = graphene.List(ClaimGQLType)


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
            .get(
                mission_code=mission_code
            )
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

        return ClaimSampleResultGQLType(
            category_one=ClaimSampleCategoryGQLType(
                category="1",
                total_category=build_category_result(mission, "1"),
                claims=category_one_claims,
            ),
            category_two=ClaimSampleCategoryGQLType(
                category="2",
                total_category=build_category_result(mission, "2"),
                claims=category_two_claims,
            ),
            category_three=ClaimSampleCategoryGQLType(
                category="3",
                total_category=build_category_result(mission, "3"),
                claims=category_three_claims,
            ),
            category_four=ClaimSampleCategoryGQLType(
                category="4",
                total_category=build_category_result(mission, "4"),
                claims=category_four_claims,
            )
        )


def build_category_result(
    mission,
    category,
):
    selected_claims = Claim.objects.filter(
        id__in=(
            FilteredClaimsForMission.objects
            .filter(
                mission=mission,
                claim_category=category,
            )
            .values_list(
                "claim_id",
                flat=True,
            )
        )
    ).distinct()

    return selected_claims.count()


class Mutation(graphene.ObjectType):
    create_mission = CreateMissionMutation.Field()
    update_mission = UpdateMissionMutation.Field()
