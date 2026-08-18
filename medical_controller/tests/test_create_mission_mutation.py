from datetime import date

from django.test import TestCase
from django.core.exceptions import ValidationError
from medical_controller.gql_mutations import (
    CreateMissionMutation,
)
from location.test_helpers import create_test_health_facility, create_test_location
from medical_controller.models import (
    MedicalControlMission,
    MissionHealthFacility,
)
from core.test_helpers import create_test_interactive_user

from location.models import (
    Location
)


class CreateMissionMutationTest(TestCase):

    def setUp(self):

        self.user = create_test_interactive_user()
        self.user.has_perms = lambda perms: True

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

    def test_create_mission(self):

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

        mission = MedicalControlMission.objects.get()

        self.assertEqual(
            mission.status,
            MedicalControlMission.STATUS_IN_PROGRESS,
        )

        self.assertEqual(
            mission.health_facilities.count(),
            2,
        )

    def test_requires_at_least_one_health_facility(self):

        with self.assertRaises(ValidationError):

            CreateMissionMutation.async_mutate(
                self.user,
                region_id=self.region.id,
                district_id=self.district.id,
                health_facility_ids=[],
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
            )

    def test_end_date_must_be_after_start_date(self):

        with self.assertRaises(ValidationError):

            CreateMissionMutation.async_mutate(
                self.user,
                region_id=self.region.id,
                district_id=self.district.id,
                health_facility_ids=[self.hf1.id],
                start_date=date(2026, 1, 31),
                end_date=date(2026, 1, 31),
            )

    def test_health_facilities_are_created(self):

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

        self.assertEqual(
            MissionHealthFacility.objects.count(),
            2,
        )
