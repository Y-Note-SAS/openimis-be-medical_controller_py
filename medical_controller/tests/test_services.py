from django.test import TestCase
from unittest.mock import patch, MagicMock
from datetime import date

from core.test_helpers import create_test_interactive_user
from location.test_helpers import create_test_location, create_test_health_facility
from location.models import Location
from claim.test_helpers import create_test_claim

from medical_controller.services import _sample_claims, process_category, _save_selected_claims
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
        )

        self.mission = MedicalControlMission.objects.get()

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
    @patch("medical_controller.services._sample_claims")
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

        result = process_category(
            mission=mission,
            category="1",
            percentage=10,
            health_facilities=[1],
            user=user
        )

        self.assertEqual(
            result,
            selected
        )

        mock_get_queryset.assert_called_once_with(
            "1",
            [1]
        )

        mock_sample.assert_called_once()

        mock_save.assert_called_once_with(
            mission,
            selected,
            "1",
            user
        )

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
