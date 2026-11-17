from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock
import math
import pytest
from django.test import TestCase
from core.test_helpers import create_test_interactive_user
from location.test_helpers import create_test_location, create_test_health_facility
from location.models import Location
from claim.test_helpers import create_test_claim

from medical_controller.services import (
    _sample_claims_by_service,
    _sample_claims,
    process_category,
    _save_selected_claims,
    _get_service_groups,
    CATEGORY_3_CODES,
    CATEGORY_5_CODES
)
from medical_controller.models import MedicalControlMission
from medical_controller.gql_mutations import CreateMissionMutation


class ServicesTest(TestCase):
    def setUp(self):
        self.user = create_test_interactive_user()

        self.region = Location.objects.create(
            code="2",
            name="East",
        )

        self.district = Location.objects.create(
            code="21",
            name="District",
        )

        location = create_test_location(loc_type="D")

        self.hf1 = create_test_health_facility(
            code="HF1",
            location_id=location.id
        )

        self.hf2 = create_test_health_facility(
            code="HF2",
            location_id=location.id
        )

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=self.district.id,
            health_facility_ids=[
                self.hf1.id,
                self.hf2.id,
            ],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=date(2026, 1, 1),
        )

        self.mission = MedicalControlMission.objects.order_by(
            "-date_created"
        ).first()

        self.claim = create_test_claim()

    def test_sample_claims_returns_empty_when_queryset_empty(self):

        queryset = MagicMock()
        queryset.values_list.return_value.distinct.return_value = []

        result = _sample_claims(queryset, 10)

        self.assertEqual(result, [])

    @patch("medical_controller.services.Claim")
    def test_sample_claims_returns_empty_when_percentage_zero(
        self,
        mock_claim,
    ):

        queryset = MagicMock()
        queryset.values_list.return_value.distinct.return_value = [1, 2, 3]

        result = _sample_claims(queryset, 0)

        self.assertEqual(result, [])
        mock_claim.objects.filter.assert_not_called()

    @patch("medical_controller.services.random.sample")
    @patch("medical_controller.services.Claim")
    def test_sample_claims_returns_selected_claims(
        self,
        mock_claim,
        mock_random,
    ):

        queryset = MagicMock()
        queryset.values_list.return_value.distinct.return_value = [1, 2, 3, 4]

        mock_random.return_value = [1]

        filtered = MagicMock()
        mock_claim.objects.filter.return_value = filtered

        result = _sample_claims(queryset, 25)

        self.assertEqual(result, filtered)

        mock_claim.objects.filter.assert_called_once_with(
            id__in=[1]
        )

    @patch(
        "medical_controller.services.FilteredClaimsForMission.objects.bulk_create"
    )
    @patch(
        "medical_controller.services.FilteredClaimsForMission.objects.filter"
    )
    @patch(
        "medical_controller.services.Claim.objects.filter"
    )
    def test_save_selected_claims_creates_records(
        self,
        mock_claim_filter,
        mock_filtered_filter,
        mock_bulk_create,
    ):

        mission = self.mission
        user = self.user

        claim = self.claim

        mock_filtered_filter.return_value.values_list.return_value = []

        _save_selected_claims(
            mission,
            [claim],
            "1",
            user
        )

        mock_claim_filter.assert_called_with(
            id=claim.id
        )

        self.assertTrue(
            mock_bulk_create.called
        )

    @patch(
        "medical_controller.services.FilteredClaimsForMission.objects.bulk_create"
    )
    @patch(
        "medical_controller.services.FilteredClaimsForMission.objects.filter"
    )
    def test_save_selected_claims_skips_existing_claim(
        self,
        mock_filtered_filter,
        mock_bulk_create,
    ):

        mission = self.mission
        user = self.user

        claim = self.claim

        mock_filtered_filter.return_value.values_list.return_value = [claim.id]

        _save_selected_claims(
            mission,
            [claim],
            "1",
            user
        )

        mock_bulk_create.assert_not_called()

    @patch("medical_controller.services._save_selected_claims")
    @patch("medical_controller.services._sample_claims_by_service")  # ← Nom corrigé
    @patch("medical_controller.services._get_category_queryset")
    @patch(
        "medical_controller.services.FilteredClaimsForMission.objects.filter"
    )
    def test_process_category(
        self,
        mock_filter,
        mock_get_queryset,
        mock_sample,
        mock_save,
    ):

        mission = self.mission
        user = self.user

        queryset = MagicMock()
        remaining_queryset = MagicMock()

        mock_get_queryset.return_value = queryset
        mock_filter.return_value.values_list.return_value = [1]
        queryset.exclude.return_value = remaining_queryset

        selected = ["claim1"]
        mock_sample.return_value = selected

        # --- Test avec category "1" ---
        result = process_category(
            mission=mission,
            category="1",
            percentage=10,
            health_facilities=[1],
            user=user
        )

        self.assertEqual(result, selected)
        mock_get_queryset.assert_called_once_with("1", [1])
        mock_sample.assert_called_once()
        mock_save.assert_called_once_with(mission, selected, "1", user)

        # --- Reset des mocks avant le 2ème test ---
        mock_filter.reset_mock()
        mock_get_queryset.reset_mock()
        mock_sample.reset_mock()
        mock_save.reset_mock()

        # Reconfigurer les retours après reset
        mock_filter.return_value.values_list.return_value = [1]
        mock_get_queryset.return_value = queryset
        mock_sample.return_value = selected

        # --- Test avec category "5" ---
        result = process_category(
            mission=mission,
            category="5",
            percentage=10,
            health_facilities=[1],
            user=user
        )

        self.assertEqual(result, selected)
        mock_get_queryset.assert_called_once_with("5", [1])
        mock_sample.assert_called_once()
        mock_save.assert_called_once_with(mission, selected, "5", user)

    @patch("medical_controller.services._save_selected_claims")
    @patch("medical_controller.services._sample_claims")
    @patch("medical_controller.services._get_category_queryset")
    @patch(
        "medical_controller.services.FilteredClaimsForMission.objects.filter"
    )
    def test_process_category_unknown_category(
        self,
        mock_filter,
        mock_get_queryset,
        mock_sample,
        mock_save,
    ):

        queryset = MagicMock()
        remaining_queryset = MagicMock()

        mock_get_queryset.return_value = queryset
        queryset.exclude.return_value = remaining_queryset

        mock_filter.return_value.values_list.return_value = []

        mock_sample.return_value = []

        result = process_category(
            mission=MagicMock(),
            category="99",
            percentage=10,
            health_facilities=[],
            user=MagicMock()
        )

        self.assertEqual(result, [])


class FakeQuerySet:
    """
    Simule un queryset contenant des Claims répartis par type de service.
    """

    def __init__(self, groups):
        self.groups = groups

    def filter(self, service_filter):
        """Return a fake query set for tests"""
        return FakeQuerySet(
            {
                code: claims
                for code, claims in self.groups.items()
                if code == service_filter
            }
        )

    def values_list(self, field, flat=False):
        """Retuen values as list"""
        claims = []
        for group_claims in self.groups.values():
            claims.extend(group_claims)

        return FakeValuesList(claims)


class FakeValuesList(list):
    """Class to return a list"""

    def distinct(self):
        """return dinctict values"""
        return FakeValuesList(set(self))


@pytest.fixture
def claims_by_service():
    """Retuns a dict of services code with values"""
    return {
        "PCS40": list(range(1, 101)),
        "PCS42": list(range(101, 301)),
        "PCS50": list(range(301, 351)),
    }


def make_fake_queryset(groups):
    """Returns a fake queryset"""
    return FakeQuerySet(groups)


def test_category_3_has_expected_service_groups():
    """Test if category 3 has expected service groups"""
    groups = _get_service_groups("3")

    assert list(groups.keys()) == [
        "PCS40",
        "PCS42",
        "PCS50",
    ]


def test_category_5_has_all_service_groups():
    """Test if category 5 has expected service groups"""
    groups = _get_service_groups("5")

    expected_prefixes = [
        "NW", "SW", "OU", "ES", "AD",
        "EN", "NO", "LT", "CE", "SU",
    ]

    expected_codes = expected_prefixes + CATEGORY_5_CODES

    assert list(groups.keys()) == expected_codes
    assert len(groups) == 12


def test_category_3_selects_10_percent_per_service(
    claims_by_service,
    monkeypatch,
):
    """Test category 3 with percentage"""
    queryset = make_fake_queryset(claims_by_service)

    # Pour isoler le calcul des pourcentages,
    # on remplace les Q objects par les codes de service.
    groups = {
        code: code
        for code in CATEGORY_3_CODES
    }

    monkeypatch.setattr(
        "services._get_service_groups",
        lambda category: groups,
    )

    # random.sample sélectionne les premiers éléments.
    def fake_sample(population, sample_size):
        return list(population)[:sample_size]

    monkeypatch.setattr(
        "services.random.sample",
        fake_sample,
    )

    with patch(
        "services.Claim.objects.filter",
        return_value=MagicMock(),
    ) as mock_filter:

        _sample_claims_by_service(
            queryset,
            "3",
            10,
        )

    # PCS40 : 100 * 10% = 10
    # PCS42 : 200 * 10% = 20
    # PCS50 : 50 * 10% = 5
    selected_ids = set()

    for _, claims in claims_by_service.items():
        expected = math.ceil(
            len(claims) * Decimal("10") / Decimal("100")
        )
        selected_ids.update(claims[:expected])

    mock_filter.assert_called_once_with(
        id__in=selected_ids
    )


def test_category_3_uses_ceil_for_rounding(monkeypatch):
    """Test category 3 and rounding"""
    groups = {
        "PCS40": "PCS40",
        "PCS42": "PCS42",
        "PCS50": "PCS50",
    }

    queryset = make_fake_queryset({
        "PCS40": list(range(1, 12)),  # 11 claims
        "PCS42": list(range(12, 14)),  # 2 claims
        "PCS50": list(range(14, 17)),  # 3 claims
    })

    monkeypatch.setattr(
        "services._get_service_groups",
        lambda category: groups,
    )

    sampled = []

    def fake_sample(population, sample_size):
        sampled.append(sample_size)
        return list(population)[:sample_size]

    monkeypatch.setattr(
        "services.random.sample",
        fake_sample,
    )

    with patch("services.Claim.objects.filter"):
        _sample_claims_by_service(
            queryset,
            "3",
            10,
        )

    # ceil(11 * 10%) = 2
    # ceil(2 * 10%) = 1
    # ceil(3 * 10%) = 1
    assert sampled == [2, 1, 1]


def test_empty_service_group_is_ignored(monkeypatch):
    """Test ignored service group"""
    groups = {
        "PCS40": "PCS40",
        "PCS42": "PCS42",
        "PCS50": "PCS50",
    }

    queryset = make_fake_queryset({
        "PCS40": list(range(1, 11)),
        "PCS42": [],
        "PCS50": list(range(11, 21)),
    })

    monkeypatch.setattr(
        "services._get_service_groups",
        lambda category: groups,
    )

    sampled = []

    def fake_sample(population, sample_size):
        sampled.append(sample_size)
        return list(population)[:sample_size]

    monkeypatch.setattr(
        "services.random.sample",
        fake_sample,
    )

    with patch("services.Claim.objects.filter"):
        _sample_claims_by_service(
            queryset,
            "3",
            10,
        )

    assert sampled == [1, 1]


@pytest.mark.parametrize(
    "percentage, expected",
    [
        (0, 0),
        (10, 10),
        (50, 50),
        (100, 100),
    ],
)
def test_sample_claims_percentage(percentage, expected):
    """Test claims with percentage"""
    claims = list(range(100))

    queryset = make_fake_queryset({
        "PCS40": claims,
    })

    # Test de la fonction de sélection classique.
    with patch(
        "services.Claim.objects.filter",
        return_value="selected_claims",
    ) as mock_filter:

        with patch(
            "services.random.sample",
            side_effect=lambda population, size: list(population)[:size],
        ):
            result = _sample_claims(
                queryset,
                percentage,
            )

    assert result == "selected_claims"

    selected_ids = mock_filter.call_args.kwargs["id__in"]

    assert len(selected_ids) == expected
