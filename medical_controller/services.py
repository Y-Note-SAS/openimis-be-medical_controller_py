import math
import uuid
import random
from decimal import Decimal
from claim.models import Claim
from medical.models import PackageTypes
from django.db.models import Q
from medical_controller.models import (
    FilteredClaimsForMission,
)


CATEGORY_3_CODES = [
    "PCS40",
    "PCS42",
    "PCS50",
]

CATEGORY_5_CODES = [
    "FCS17",
    "FCS13"
]

def _get_service_groups(category):
    if category == "3":
        return {
            code: Q(services__service__code=code)
            for code in CATEGORY_3_CODES
        }

    if category == "5":
        groups = {
            code: Q(services__service__code__startswith=code)
            for code in [
                "NW", "SW", "OU", "ES", "AD",
                "EN", "NO", "LT", "CE", "SU",
            ]
        }

        groups.update({
            code: Q(services__service__code=code)
            for code in CATEGORY_5_CODES
        })

        return groups

    return None


def _sample_claims_by_service(
    queryset,
    category,
    percentage,
):
    service_groups = _get_service_groups(category)

    if service_groups is None:
        return _sample_claims(queryset, percentage)

    selected_ids = set()

    for service_filter in service_groups.values():
        service_claim_ids = list(
            queryset.filter(service_filter)
            .values_list("id", flat=True)
            .distinct()
        )

        if not service_claim_ids:
            continue

        sample_size = math.ceil(
            len(service_claim_ids)
            * Decimal(str(percentage))
            / Decimal("100")
        )

        sample_size = min(
            sample_size,
            len(service_claim_ids),
        )

        if sample_size:
            selected_ids.update(
                random.sample(
                    service_claim_ids,
                    sample_size,
                )
            )

    return Claim.objects.filter(id__in=selected_ids)

def _sample_claims(queryset, percentage):
    claim_ids = list(
        queryset.values_list(
            "id",
            flat=True,
        ).distinct()
    )

    if not claim_ids:
        return []

    sample_size = math.ceil(
        len(claim_ids)
        * (Decimal(str(percentage)) / Decimal("100"))
    )

    sample_size = min(
        sample_size,
        len(claim_ids),
    )

    if sample_size == 0:
        return []

    selected_ids = random.sample(
        claim_ids,
        sample_size,
    )

    return Claim.objects.filter(
        id__in=selected_ids
    )


def _save_selected_claims(
    mission,
    claims,
    category,
    user
):
    existing_ids = set(
        FilteredClaimsForMission.objects.filter(
            mission=mission,
        ).values_list(
            "claim_id",
            flat=True,
        )
    )

    objects = []

    for claim in claims:
        Claim.objects.filter(id=claim.id).update(claim_category=category)
        if claim.id in existing_ids:
            continue

        objects.append(
            FilteredClaimsForMission(
                id=uuid.uuid4(),
                mission=mission,
                claim=claim,
                claim_category=category,
                audited=False,
                from_rejected_to_valuated=False,
                user_created=user,
                user_updated=user,
            )
        )

    if objects:
        FilteredClaimsForMission.objects.bulk_create(
            objects
        )


def _get_category_queryset(
    category,
    health_facilities,
):
    base_queryset = Claim.objects.filter(
        validity_to__isnull=True,
        health_facility_id__in=health_facilities,
    )

    if category == "1":
        return (
            base_queryset
            .filter(
                status=Claim.STATUS_VALUATED,
                services__service__packagetype=PackageTypes.P,
            )
            .distinct()
        )

    if category == "2":
        return (
            base_queryset
            .filter(
                status=Claim.STATUS_VALUATED,
                services__service__packagetype=PackageTypes.F,
            )
            .exclude(
                services__service__code__in=(
                    CATEGORY_3_CODES
                )
            )
            .distinct()
        )

    if category == "3":
        return (
            base_queryset
            .filter(
                status=Claim.STATUS_VALUATED,
                services__service__code__in=(
                    CATEGORY_3_CODES
                )
            )
            .distinct()
        )

    if category == "4":
        return (
            base_queryset
            .filter(
                status=Claim.STATUS_REJECTED,
                services__rejection_reason=-1,
            )
            .distinct()
        )

    if category == "5":
        starts_with_q = Q()
        for prefix in ["NW", "SW", "OU", "ES", "AD", "EN", "NO", "LT", "CE", "SU"]:
            starts_with_q |= Q(services__service__code__startswith=prefix)

        return (
            base_queryset.filter(
                status=Claim.STATUS_VALUATED,
            ).filter(
                Q(services__service__code__in=CATEGORY_5_CODES) | starts_with_q
            ).distinct()
        )

    return Claim.objects.none()


def process_category(
    mission,
    category,
    percentage,
    health_facilities,
    user
):
    queryset = _get_category_queryset(
        category,
        health_facilities,
    )

    already_selected_ids = (
        FilteredClaimsForMission.objects
        .filter(
            mission=mission,
            claim_category=category,
        ).values_list("claim_id", flat=True)
    )

    remaining_queryset = queryset.exclude(
        id__in=already_selected_ids,
    )

    selected_claims = _sample_claims_by_service(
        remaining_queryset,
        category,
        percentage,
    )

    _save_selected_claims(
        mission,
        selected_claims,
        category,
        user
    )
    return selected_claims
