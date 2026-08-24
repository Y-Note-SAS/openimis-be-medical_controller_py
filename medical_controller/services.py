import math
import uuid
import random
from django.utils.translation import gettext as _
from decimal import Decimal
from claim.models import Claim
from medical.models import PackageTypes
from medical_controller.models import (
    FilteredClaimsForMission,
)


CATEGORY_3_CODES = [
    "PCS40",
    "PCS42",
    "PCS50",
]


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

    claims.update(claim_category=category)

    for claim in claims:
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
        )
        .values_list(
            "claim_id",
            flat=True,
        )
    )

    remaining_queryset = queryset.exclude(
        id__in=already_selected_ids,
    )

    selected_claims = _sample_claims(
        remaining_queryset,
        percentage,
    )

    _save_selected_claims(
        mission,
        selected_claims,
        category,
        user
    )
    return selected_claims
