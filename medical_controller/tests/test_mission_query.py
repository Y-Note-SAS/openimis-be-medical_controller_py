from datetime import date
from unittest.mock import patch

from django.test import TestCase

from medical_controller.schema import Query
from medical_controller.models import MedicalControlMission
from core.test_helpers import create_test_interactive_user
from location.models import Location


class MissionQueryTest(TestCase):

    def setUp(self):
        self.user = create_test_interactive_user()

        # On évite de remplacer has_perms par une lambda persistante.
        # On le mockera dans chaque test.

        self.region = Location(
            code="2",
            name="East",
        )
        self.region.save()

        self.district = Location(
            code="21",
            name="District",
        )
        self.district.save()

        self.mission = MedicalControlMission(
            mission_code="200001",
            region=self.region,
            district=self.district,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            status=MedicalControlMission.STATUS_IN_PROGRESS,
            user=self.user,
        )
        self.mission.save(username=self.user.username)

        class Context:
            pass

        self.context = Context()
        self.context.user = self.user

        class Info:
            pass

        self.info = Info()
        self.info.context = self.context

    @patch("medical_controller.schema.gql_optimizer.query")
    def test_filter_by_region(
        self,
        mock_optimizer
    ):
        """
        Le filtre region_id doit sélectionner uniquement
        les missions de la région demandée.
        """

        # Le resolver doit retourner le queryset avant optimisation
        mock_optimizer.side_effect = lambda queryset, info: queryset

        with patch.object(
            self.user,
            "has_perms",
            return_value=True,
        ):
            result = Query().resolve_missions(
                info=self.info,
                region_id=self.region.id,
            )

        self.assertEqual(result.count(), 1)
        self.assertEqual(
            result.first().pk,
            self.mission.pk,
        )

    @patch("medical_controller.schema.gql_optimizer.query")
    def test_filter_by_status(self, mock_optimizer):
        """
        Le filtre status doit sélectionner les missions
        ayant le statut demandé.
        """

        mock_optimizer.side_effect = lambda queryset, info: queryset

        with patch.object(
            self.user,
            "has_perms",
            return_value=True,
        ):
            result = Query().resolve_missions(
                info=self.info,
                status=MedicalControlMission.STATUS_IN_PROGRESS,
            )

        self.assertEqual(result.count(), 1)
        self.assertEqual(
            result.first().status,
            MedicalControlMission.STATUS_IN_PROGRESS,
        )

    @patch("medical_controller.schema.gql_optimizer.query")
    def test_filter_by_mission_code(self, mock_optimizer):
        """
        Le filtre mission_code doit retourner la mission correspondante.
        """

        mock_optimizer.side_effect = lambda queryset, info: queryset

        with patch.object(
            self.user,
            "has_perms",
            return_value=True,
        ):
            result = Query().resolve_missions(
                info=self.info,
                mission_code="200001",
            )

        self.assertEqual(result.count(), 1)
        self.assertEqual(
            result.first().mission_code,
            "200001",
        )

    @patch("medical_controller.schema.gql_optimizer.query")
    def test_unknown_code_returns_empty_queryset(
        self,
        mock_optimizer,
    ):
        """
        Un code inexistant doit retourner un queryset vide.
        """

        mock_optimizer.side_effect = lambda queryset, info: queryset

        with patch.object(
            self.user,
            "has_perms",
            return_value=True,
        ):
            result = Query().resolve_missions(
                info=self.info,
                mission_code="XXX",
            )

        self.assertEqual(result.count(), 0)

    @patch("medical_controller.schema.gql_optimizer.query")
    def test_filter_by_district(self, mock_optimizer):
        """
        Le filtre district_id doit sélectionner les missions
        du district demandé.
        """

        mock_optimizer.side_effect = lambda queryset, info: queryset

        with patch.object(
            self.user,
            "has_perms",
            return_value=True,
        ):
            result = Query().resolve_missions(
                info=self.info,
                district_id=self.district.id,
            )

        self.assertEqual(result.count(), 1)
        self.assertEqual(
            result.first().district_id,
            self.district.id,
        )

    @patch("medical_controller.schema.gql_optimizer.query")
    def test_combined_filters(self, mock_optimizer):

        mock_optimizer.side_effect = lambda queryset, info: queryset

        with patch.object(
            self.user,
            "has_perms",
            return_value=True,
        ):
            result = Query().resolve_missions(
                self.info,
                region_id=self.region.id,
                district_id=self.district.id,
                status=MedicalControlMission.STATUS_IN_PROGRESS,
                mission_code="200001",
            )

        self.assertEqual(result.count(), 1)

        mission = result.first()

        self.assertEqual(mission.pk, self.mission.pk)
        self.assertEqual(mission.region_id, self.region.id)
        self.assertEqual(mission.district_id, self.district.id)
        self.assertEqual(
            mission.status,
            MedicalControlMission.STATUS_IN_PROGRESS,
        )
        self.assertEqual(
            mission.mission_code,
            "200001",
        )


    @patch("medical_controller.schema.gql_optimizer.query")
    def test_unauthorized_user_is_rejected(self, mock_optimizer):
        """
        Un utilisateur sans permission ne doit pas pouvoir
        consulter les missions.
        """

        from django.core.exceptions import PermissionDenied

        mock_optimizer.side_effect = lambda queryset, info: queryset

        with patch.object(
            self.user,
            "has_perms",
            return_value=False,
        ):
            with self.assertRaises(PermissionDenied):
                Query().resolve_missions(
                    self.info,
                )
