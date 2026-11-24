from datetime import date
import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AnonymousUser
from location.test_helpers import create_test_health_facility, create_test_location
from core.test_helpers import create_test_interactive_user
from claim.test_helpers import create_test_claim
from location.models import Location
from medical_controller.gql_mutations import (
    CreateMissionMutation,
    UpdateMissionMutation,
    TreatClaimsMutation
)
from medical_controller.models import (
    MedicalControlMission,
    MissionHealthFacility,
    MissionActivityHistory,
    FilteredClaimsForMission,
    MissionDistricts
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

        # Créer des claims pour les tests
        self.claim_adoptable = create_test_claim(
            custom_props={
                "status": 2
            }
        )
        self.claim2 = create_test_claim(
            custom_props={
                "status": 2
            }
        )
        self.claim_rejected = create_test_claim(
            custom_props={
                "status": 1
            }
        )
        self.claim3 = create_test_claim(
            custom_props={
                "status": 1
            }
        )
        self.claim_non_rejected = create_test_claim(
            custom_props={
                "status": 2
            }
        )

    def test_create_mission(self):

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=[self.district.id],
            health_facility_ids=[
                self.hf1.id,
                self.hf2.id,
            ],
            start_date=date(2026, 1, 1),
            mission_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        mission = MedicalControlMission.objects.order_by(
            "-date_created"
        ).first()

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
                district_id=[self.district.id],
                health_facility_ids=[],
                start_date=date(2026, 1, 1),
                mission_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
            )

    def test_end_date_must_be_after_start_date(self):

        with self.assertRaises(ValidationError):

            CreateMissionMutation.async_mutate(
                self.user,
                region_id=self.region.id,
                district_id=[self.district.id],
                health_facility_ids=[self.hf1.id],
                start_date=date(2026, 1, 31),
                mission_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
            )

    def test_health_facilities_are_created(self):

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=[self.district.id],
            health_facility_ids=[
                self.hf1.id,
                self.hf2.id,
            ],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=date(2026, 1, 1),
        )

        self.assertTrue(
            MissionHealthFacility.objects.count() > 0
        )

    def test_create_mission_requires_authenticated_user(self):

        with self.assertRaises(ValidationError):
            CreateMissionMutation.async_mutate(
                AnonymousUser(),
                region_id=self.region.id,
                district_id=[self.district.id],
                health_facility_ids=[self.hf1.id],
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                mission_date=date(2026, 1, 1),
            )

    def test_first_mission_code_is_generated(self):

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=[self.district.id],
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=date(2026, 1, 1),
        )

        mission = MedicalControlMission.objects.order_by(
            "-date_created"
        ).first()

        self.assertEqual(
            mission.mission_code,
            "200001"
        )

    def test_mission_code_is_incremented(self):

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=[self.district.id],
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=date(2026, 1, 1),
        )

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=[self.district.id],
            health_facility_ids=[self.hf2.id],
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            mission_date=date(2026, 1, 1),
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
            district_id=[self.district.id],
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=date(2026, 1, 1),
        )

        self.assertTrue(
            MissionActivityHistory.objects.count() > 0
        )

    def test_update_mission_status(self):

        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_id=[self.district.id],
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=date(2026, 1, 1),
        )

        mission = MedicalControlMission.objects.order_by(
            "-date_created"
        ).first()

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
            district_id=[self.district.id],
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=date(2026, 1, 1),
        )

        mission = MedicalControlMission.objects.order_by(
            "-date_created"
        ).first()

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
            district_id=[self.district.id],
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=date(2026, 1, 1),
        )

        mission = MedicalControlMission.objects.order_by(
            "-date_created"
        ).first()

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

    def test_districts_are_created(self):
        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_ids=[self.district.id],
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=date(2026, 1, 1),
        )

        mission = MedicalControlMission.objects.order_by(
            "-date_created"
        ).first()

        self.assertEqual(
            MissionDistricts.objects.filter(mission=mission).count(),
            1
        )

    def test_only_mission_chief_can_close_mission(self):
        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_ids=[self.district.id],
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=date(2026, 1, 1),
        )

        mission = MedicalControlMission.objects.order_by(
            "-date_created"
        ).first()

        with self.assertRaises(ValidationError) as ctx:
            UpdateMissionMutation.async_mutate(
                AnonymousUser(),
                mission_code=mission.mission_code,
                status="C"
            )
            self.assertIn("authentication_required", str(ctx.exception))

    def test_update_mission_can_close_when_all_claims_are_audited(self):
        CreateMissionMutation.async_mutate(
            self.user,
            region_id=self.region.id,
            district_ids=[self.district.id],
            health_facility_ids=[self.hf1.id],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=date(2026, 1, 1),
        )

        mission = MedicalControlMission.objects.order_by(
            "-date_created"
        ).first()

        result = UpdateMissionMutation.async_mutate(
            self.user,
            mission_code=mission.mission_code,
            status="C"
        )

        mission.refresh_from_db()

        self.assertEqual(mission.status, "C")
        self.assertIsNone(result)

    def test_anonymous_user_raises_error(self):
        with self.assertRaises(ValidationError) as ctx:
            TreatClaimsMutation.async_mutate(
                AnonymousUser(),
                action="adopt",
                claim_ids=[self.claim_adoptable.id]
            )
        self.assertIn("authentication_required", str(ctx.exception))

    def test_none_user_raises_error(self):
        with self.assertRaises(ValidationError) as ctx:
            TreatClaimsMutation.async_mutate(
                None,
                action="adopt",
                claim_ids=[self.claim_adoptable.id]
            )
        self.assertIn("authentication_required", str(ctx.exception))

    # ─── Tests action manquante/invalide ───

    def test_no_action_raises_error(self):
        with self.assertRaises(ValidationError) as ctx:
            TreatClaimsMutation.async_mutate(
                self.user,
                claim_ids=[self.claim_adoptable.id]
            )
        self.assertIn("no_action_sent_for_treat_claims", str(ctx.exception))

    def test_empty_action_raises_error(self):
        with self.assertRaises(ValidationError) as ctx:
            TreatClaimsMutation.async_mutate(
                self.user,
                action="",
                claim_ids=[self.claim_adoptable.id]
            )
        self.assertIn("no_action_sent_for_treat_claims", str(ctx.exception))

    def test_invalid_action_raises_error(self):
        with self.assertRaises(ValidationError) as ctx:
            TreatClaimsMutation.async_mutate(
                self.user,
                action="delete",
                claim_ids=[self.claim_adoptable.id]
            )
        self.assertIn("action_must_be_adopt_or_rehabilitate", str(ctx.exception))

    # ─── Tests claim_ids manquant ───

    def test_no_claim_ids_raises_error(self):
        with self.assertRaises(ValidationError) as ctx:
            TreatClaimsMutation.async_mutate(
                self.user,
                action="adopt"
            )
        self.assertIn("no_claim_ids_sent_for_treat_claims", str(ctx.exception))

    def test_empty_claim_ids_raises_error(self):
        with self.assertRaises(ValidationError) as ctx:
            TreatClaimsMutation.async_mutate(
                self.user,
                action="adopt",
                claim_ids=[]
            )
        self.assertIn("no_claim_ids_sent_for_treat_claims", str(ctx.exception))

    # ─── Tests action "adopt" ───

    def test_adopt_sets_audit_status_to_A(self):
        result = TreatClaimsMutation.async_mutate(
            self.user,
            action="adopt",
            claim_ids=[self.claim_adoptable.id]
        )
        self.claim_adoptable.refresh_from_db()
        self.assertEqual(self.claim_adoptable.audit_status, 'A')
        self.assertIsNone(result)

    def test_adopt_on_multiple_claims(self):
        result = TreatClaimsMutation.async_mutate(
            self.user,
            action="adopt",
            claim_ids=[self.claim_adoptable.id, self.claim2.id]
        )
        self.claim_adoptable.refresh_from_db()
        self.claim2.refresh_from_db()
        self.assertEqual(self.claim_adoptable.audit_status, 'A')
        self.assertEqual(self.claim2.audit_status, 'A')
        self.assertIsNone(result)

    # ─── Tests action "rehabilitate" ───

    def test_rehabilitate_on_rejected_claim_sets_audit_status_to_H(self):
        result = TreatClaimsMutation.async_mutate(
            self.user,
            action="rehabilitate",
            claim_ids=[self.claim_rejected.id]
        )
        self.claim_rejected.refresh_from_db()
        self.assertEqual(self.claim_rejected.audit_status, 'H')
        self.assertIsNone(result)

    def test_rehabilitate_on_multiple_rejected_claims_succeeds(self):
        result = TreatClaimsMutation.async_mutate(
            self.user,
            action="rehabilitate",
            claim_ids=[self.claim_rejected.id, self.claim3.id]
        )
        self.claim_rejected.refresh_from_db()
        self.claim3.refresh_from_db()
        self.assertEqual(self.claim_rejected.audit_status, 'H')
        self.assertEqual(self.claim3.audit_status, 'H')
        self.assertIsNone(result)

    def test_rehabilitate_on_non_rejected_claim_raises_error(self):
        with self.assertRaises(ValidationError) as ctx:
            TreatClaimsMutation.async_mutate(
                self.user,
                action="rehabilitate",
                claim_ids=[self.claim_non_rejected.id]
            )
        self.assertIn("Cannot rehabilitate", str(ctx.exception))
        self.assertIn(self.claim_non_rejected.code, str(ctx.exception))

    def test_rehabilitate_mixed_rejected_and_non_rejected_raises_error(self):
        with self.assertRaises(ValidationError) as ctx:
            TreatClaimsMutation.async_mutate(
                self.user,
                action="rehabilitate",
                claim_ids=[self.claim_rejected.id, self.claim_non_rejected.id]
            )
        self.assertIn("Cannot rehabilitate", str(ctx.exception))
        self.assertIn(self.claim_non_rejected.code, str(ctx.exception))

        # Vérifier que le claim rejected n'a PAS été modifié (atomicité)
        self.claim_rejected.refresh_from_db()
        self.assertNotEqual(self.claim_rejected.audit_status, 'H')
