from datetime import date
import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError
from medical_controller.gql_mutations import (
    CreateMissionMutation,
    UpdateMissionMutation
)
from location.test_helpers import create_test_health_facility, create_test_location
from medical_controller.models import (
    MedicalControlMission,
    MissionHealthFacility,
    MissionActivityHistory,
    FilteredClaimsForMission
)
from core.test_helpers import create_test_interactive_user
from claim.test_helpers import create_test_claim
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

    def test_create_mission_requires_authenticated_user(self):
        from django.contrib.auth.models import AnonymousUser

        with self.assertRaises(ValidationError):
            CreateMissionMutation.async_mutate(
                AnonymousUser(),
                region_id=self.region.id,
                district_id=self.district.id,
                health_facility_ids=[self.hf1.id],
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
            )

    def test_first_mission_code_is_generated(self):

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=self.district.id,
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        mission = MedicalControlMission.objects.get()

        self.assertEqual(
            mission.mission_code,
            "200001"
        )

    def test_mission_code_is_incremented(self):

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=self.district.id,
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=self.district.id,
            health_facility_ids=[self.hf2.id],
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
        )

        mission = (
            MedicalControlMission.objects
            .order_by("-mission_code")
            .first()
        )

        self.assertEqual(
            mission.mission_code,
            "200002"
        )

    from medical_controller.models import (
        MissionActivityHistory
    )

    def test_activity_history_is_created(self):

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=self.district.id,
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        self.assertEqual(
            MissionActivityHistory.objects.count(),
            1
        )

    def test_update_mission_status(self):

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=self.district.id,
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        mission = MedicalControlMission.objects.get()

        UpdateMissionMutation.async_mutate(
            self.user,
            mission_code=mission.mission_code,
            status="C"
        )

        mission.refresh_from_db()

        self.assertEqual(
            mission.status,
            "C"
        )

    def test_update_requires_mission_code(self):

        with self.assertRaises(ValidationError):
            UpdateMissionMutation.async_mutate(
                self.user,
                status="C"
            )

    def test_update_requires_status(self):

        with self.assertRaises(ValidationError):
            UpdateMissionMutation.async_mutate(
                self.user,
                mission_code="200001"
            )

    def test_update_requires_authenticated_user(self):

        from django.contrib.auth.models import AnonymousUser

        with self.assertRaises(ValidationError):
            UpdateMissionMutation.async_mutate(
                AnonymousUser(),
                mission_code="200001",
                status="C"
            )

    def test_update_creates_history(self):

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=self.district.id,
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        mission = MedicalControlMission.objects.get()

        initial_count = MissionActivityHistory.objects.count()

        UpdateMissionMutation.async_mutate(
            self.user,
            mission_code=mission.mission_code,
            status="C"
        )

        self.assertEqual(
            MissionActivityHistory.objects.count(),
            initial_count + 1
        )

    def test_update_forbiden_when_all_claims_not_audited(self):

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=self.district.id,
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        mission = MedicalControlMission.objects.get()

        claim = create_test_claim()

        filtred_claims = FilteredClaimsForMission(
            id=uuid.uuid4(),
            mission=mission,
            claim=claim,
            claim_category="1",
            audited=False,
            from_rejected_to_valuated=False,
            user_created=self.user,
            user_updated=self.user,
        )
        filtred_claims.save(username=self.user.username)

        res = UpdateMissionMutation.async_mutate(
            self.user,
            mission_code=mission.mission_code,
            status="C"
        )
        self.assertEqual(res[0]["message"], "mutation.all_claims_not_audited")
