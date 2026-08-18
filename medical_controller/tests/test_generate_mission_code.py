from django.test import TestCase

from location.models import Location

from medical_controller.gql_mutations import (
    generate_mission_code,
)
from medical_controller.models import (
    MedicalControlMission,
)

from core.test_helpers import create_test_interactive_user


class GenerateMissionCodeTest(TestCase):

    def setUp(self):
        self.user = create_test_interactive_user()
        self.user.has_perms = lambda perms: True

        self.region = Location.objects.create(
            code="2",
            name="East",
        )

    def test_first_mission_starts_at_00001(self):

        code = generate_mission_code(self.region)

        self.assertEqual(
            code,
            "200001",
        )

    def test_next_sequence_is_incremented(self):

        mission = MedicalControlMission(
            mission_code="200001",
            region=self.region,
            district=self.region,
            start_date="2026-01-01",
            end_date="2026-01-31",
            user=self.user,
        )
        mission.save(username=self.user.username)

        code = generate_mission_code(self.region)

        self.assertEqual(
            code,
            "200002",
        )

    def test_sequence_is_independent_per_region(self):

        other_region = Location.objects.create(
            code="4",
            name="North",
        )

        mission = MedicalControlMission(
            mission_code="200001",
            region=self.region,
            district=self.region,
            start_date="2026-01-01",
            end_date="2026-01-31",
            user=self.user,
        )
        mission.save(username=self.user.username)

        code = generate_mission_code(other_region)

        self.assertEqual(
            code,
            "400001",
        )
