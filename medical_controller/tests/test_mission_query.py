from datetime import date, datetime
from unittest.mock import patch
from types import SimpleNamespace
import uuid
import graphene
from graphene.relay import Node
from django.test import TestCase
from django.core.exceptions import PermissionDenied
from location.test_helpers import create_test_location, create_test_health_facility
from core.test_helpers import create_test_interactive_user
from medical_controller.schema import Query
from medical_controller.models import (
    MedicalControlMission,
    MissionDistricts,
    MissionHealthFacility
)


class MissionQueryTest(TestCase):

    def setUp(self):
        self.user = create_test_interactive_user()

        # On évite de remplacer has_perms par une lambda persistante.
        # On le mockera dans chaque test.

        self.region = create_test_location(
            loc_type="R"
        )

        self.district = create_test_location(
            loc_type="D"
        )

        self.mission = MedicalControlMission(
            mission_code="200001",
            region=self.region,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mission_date=datetime(2026, 1, 1, 0, 0),
            status=MedicalControlMission.STATUS_IN_PROGRESS,
            user=self.user,
        )
        self.mission.save(username=self.user.username)
        self.contextquery = SimpleNamespace(
            user=self.user,
            headers={"User-Agent": "test"}
        )

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

            global_id = Node.to_global_id(
                "LocationGQLType",
                self.region.id
            )
            query = """
                query($region: ID!){
                    missions(region_Id: $region){
                        edges{
                        node{
                            missionCode
                        }
                        }
                    }
                }
            """
            variables = {
                "region": global_id
            }
            schema = graphene.Schema(
                query=Query
            )

            result = schema.execute(
                query,
                variables=variables,
                context_value=self.contextquery
            )
            self.assertEqual(
                len(
                    result.data["missions"]["edges"]
                ),
                1,
            )

            self.assertEqual(
                len(
                    result.data["missions"]["edges"]
                ),
                1,
            )
            mission_district = MissionDistricts(
                id=uuid.uuid4(),
                mission=self.mission,
                user_created=self.user,
                user_updated=self.user,
                district_id=self.district.id,
            )
            mission_district.save(username=self.user.username)

            query = """
                query($districts: [ID!]!) {
                    missions(districts_District_Id_In: $districts) {
                        edges {
                            node {
                                missionCode
                            }
                        }
                    }
                }
            """

            global_id = Node.to_global_id(
                "LocationGQLType",
                self.district.id
            )

            variables = {
                "districts": [global_id]
            }

            schema = graphene.Schema(query=Query)

            result = schema.execute(
                query,
                variables=variables,
                context_value=self.contextquery
            )

            self.assertIsNone(result.errors, result.errors)

            self.assertEqual(
                len(result.data["missions"]["edges"]),
                1,
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
            query = """
                query($status: MedicalControlMissionStatus!){
                    missions(status: $status){
                        edges{
                        node{
                            missionCode
                            status
                        }
                        }
                    }
                }
            """
            variables = {
                "status": MedicalControlMission.STATUS_IN_PROGRESS
            }
            schema = graphene.Schema(
                query=Query
            )

            result = schema.execute(
                query,
                variables=variables,
                context_value=self.contextquery
            )

            self.assertEqual(
                len(
                    result.data["missions"]["edges"]
                ),
                1,
            )
            self.assertEqual(
                result.data["missions"]["edges"][0]["node"]["status"],
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
            query = """
                query($missionCode: String!){
                    missions(missionCode: $missionCode){
                        edges{
                        node{
                            missionCode
                        }
                        }
                    }
                }
            """
            variables = {
                "missionCode": "200001"
            }
            schema = graphene.Schema(
                query=Query
            )

            result = schema.execute(
                query,
                variables=variables,
                context_value=self.contextquery
            )

            self.assertEqual(
                len(
                    result.data["missions"]["edges"]
                ),
                1,
            )
            self.assertEqual(
                result.data["missions"]["edges"][0]["node"]["missionCode"],
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
            query = """
                query($missionCode: String!){
                    missions(missionCode: $missionCode){
                        edges{
                        node{
                            missionCode
                        }
                        }
                    }
                }
            """
            variables = {
                "missionCode": "xxx"
            }
            schema = graphene.Schema(
                query=Query
            )

            result = schema.execute(
                query,
                variables=variables,
                context_value=self.contextquery
            )

            self.assertEqual(
                len(
                    result.data["missions"]["edges"]
                ),
                0,
            )

    @patch("medical_controller.schema.gql_optimizer.query")
    def test_filter_by_districts(self, mock_optimizer):
        """
        Le filtre district_id doit sélectionner les missions
        du district demandé.
        """
        mock_optimizer.side_effect = lambda queryset, info: queryset

        with patch.object(self.user, "has_perms", return_value=True):
            mission_district = MissionDistricts(
                id=uuid.uuid4(),
                mission=self.mission,
                user_created=self.user,
                user_updated=self.user,
                district_id=self.district.id,
            )
            mission_district.save(username=self.user.username)

            code = self.mission.mission_code
            query = """
                query($missionCode: String!) {
                    missionsDistricts(mission_MissionCode: $missionCode) {
                        edges {
                            node {
                                district {
                                    id name
                                }
                            }
                        }
                    }
                }
            """
            variables = {"missionCode": code}
            schema = graphene.Schema(query=Query)

            result = schema.execute(
                query,
                variables=variables,
                context_value=self.contextquery,
            )

            self.assertEqual(
                len(result.data["missionsDistricts"]["edges"]),
                1,
            )
            self.assertEqual(
                result.data["missionsDistricts"]["edges"][0]["node"]["district"]["name"],
                self.district.name,
            )

    @patch("medical_controller.schema.gql_optimizer.query")
    def test_combined_filters(self, mock_optimizer):

        mock_optimizer.side_effect = lambda queryset, info: queryset

        with patch.object(
            self.user,
            "has_perms",
            return_value=True,
        ):
            query = """
                query(
                    $region: ID!,
                    $status: MedicalControlMissionStatus!,
                    $missionCode: String!
                ) {
                    missions(
                        region_Id: $region,
                        status: $status,
                        missionCode: $missionCode
                    ) {
                        totalCount
                        edges {
                            node {
                                missionCode
                                region {
                                    code
                                }
                                districts {
                                    edges {
                                        node {
                                            district {
                                                id name
                                            }
                                        }
                                    }
                                }
                                status
                            }
                        }
                    }
                }
            """

            variables = {
                "region": Node.to_global_id(
                    "LocationGQLType",
                    self.region.id
                ),
                "status": MedicalControlMission.STATUS_IN_PROGRESS,
                "missionCode": self.mission.mission_code,
            }

            schema = graphene.Schema(query=Query)

            result = schema.execute(
                query,
                variables=variables,
                context_value=self.contextquery,
            )

            self.assertEqual(
                len(
                    result.data["missions"]["edges"]
                ),
                1,
            )

            self.assertEqual(
                result.data["missions"]["edges"][0]["node"]["region"]["code"], self.region.code)
            self.assertEqual(
                result.data["missions"]["edges"][0]["node"]["status"],
                MedicalControlMission.STATUS_IN_PROGRESS,
            )
            self.assertEqual(
                result.data["missions"]["edges"][0]["node"]["missionCode"],
                self.mission.mission_code,
            )

    @patch("medical_controller.schema.gql_optimizer.query")
    def test_filter_by_mission_date(self, mock_optimizer):
        """Le filtre mission_date doit selectionner les missions de l'intervalle."""
        mock_optimizer.side_effect = lambda queryset, info: queryset

        with patch.object(self.user, "has_perms", return_value=True):
            schema = graphene.Schema(query=Query)
            query = """
                query($from: DateTime!, $to: DateTime!){
                    missions(missionDate_Gte: $from, missionDate_Lte: $to){
                        edges{ node{ missionCode } }
                    }
                }
            """
            result = schema.execute(
                query,
                variables={"from": "2026-01-01T00:00:00", "to": "2026-01-31T23:59:59"},
                context_value=self.contextquery,
            )
            self.assertEqual(len(result.data["missions"]["edges"]), 1)
            self.assertEqual(
                result.data["missions"]["edges"][0]["node"]["missionCode"], "200001"
            )

            result_out = schema.execute(
                query,
                variables={"from": "2026-02-01T00:00:00", "to": "2026-02-28T23:59:59"},
                context_value=self.contextquery,
            )
            self.assertEqual(len(result_out.data["missions"]["edges"]), 0)


class TestGetAvailableDistrictsAndHF(TestCase):
    """Test for check mission availabilty"""

    def setUp(self):
        self.user = create_test_interactive_user()
        self.user.has_perms = lambda perms: True

        self.contextquery = SimpleNamespace(
            user=self.user,
            headers={"User-Agent": "test"}
        )

        self.info = SimpleNamespace(
            context=SimpleNamespace(user=self.user)
        )

        # Création des districts
        self.district_4 = create_test_location(
            "D",
            custom_props={
                "code": "D004",
                "name": "District 4"
            }
        )
        self.district_5 = create_test_location(
            "D",
            custom_props={
                "code": "D005",
                "name": "District 5"
            }
        )

        self.region = create_test_location(
            "R",
            custom_props={
                "code": "R001",
                "name": "Region 1"
            }
        )

        # Création des FOSA
        self.hf_1 = create_test_health_facility(
            "HF001",
            self.district_4
        )
        self.hf_2 = create_test_health_facility(
            "HF002",
            location_id=self.district_4
        )
        self.hf_3 = create_test_health_facility(
            "HF003",
            location_id=self.district_5
        )
        self.hf_4 = create_test_health_facility(
            "HF004",
            location_id=self.district_5
        )

        self.start_date = date(2026, 1, 1)
        self.end_date = date(2026, 1, 31)

    def create_mission(self, mission_code, start_date, end_date):

        mission = MedicalControlMission(
            mission_code=mission_code,
            region=self.region,
            start_date=start_date,
            end_date=end_date,
            mission_date=end_date,
            status=MedicalControlMission.STATUS_IN_PROGRESS,
            user=self.user,
        )
        return mission.save(username=self.user.username)

    def assign_district(self, mission, district):

        mission_district = MissionDistricts(
            id=uuid.uuid4(),
            mission=mission,
            user_created=self.user,
            user_updated=self.user,
            district_id=district.id,
        )
        return mission_district.save(username=self.user.username)

    def assign_hf(self, mission, hf):

        mission_hf = MissionHealthFacility.objects.create(
            id=uuid.uuid4(),
            mission=mission,
            user_created=self.user,
            user_updated=self.user,
            health_facility_id=hf
        )
        return mission_hf.save(username=self.user.username)

    @patch("medical_controller.schema.gql_optimizer.query")
    def execute_available_districts_query(self, mock_optimizer):
        mock_optimizer.side_effect = lambda queryset, info: queryset

        with patch.object(
            self.user,
            "has_perms",
            return_value=True,
        ):
            query = """
                query(
                    $districtIds: [Int!]!,
                    $healthFacilityIds: [Int!]!,
                    $startDate: Date!,
                    $endDate: Date!
                ) {
                    getAvailableDistrictsAndHf(
                        districtIds: $districtIds,
                        healthFacilityIds: $healthFacilityIds,
                        startDate: $startDate,
                        endDate: $endDate
                    ) {
                        districtIds
                        healthFacilityIds
                    }
                }
            """

            variables = {
                "districtIds": [
                    self.district_4.id,
                    self.district_5.id,
                ],
                "healthFacilityIds": [
                    self.hf_1.id,
                    self.hf_2.id,
                    self.hf_3.id,
                    self.hf_4.id,
                ],
                "startDate": "2026-01-01",
                "endDate": "2026-01-31",
            }

            schema = graphene.Schema(query=Query)

            result = schema.execute(
                query,
                variables=variables,
                context_value=self.contextquery,
            )

            return result

    def test_returns_all_districts_and_hfs_when_no_mission_exists(self):
        """
        Aucune mission sur la période :
        toutes les données initiales doivent être retournées.
        """
        result = self.execute_available_districts_query()
        data = result.data

        self.assertIsNone(result.errors)

        self.assertEqual(
            set(data["checkMissionAvailability"]["districtIds"]),
            {self.district_4.id, self.district_5.id},
        )
        self.assertEqual(
            set(data["checkMissionAvailability"]["healthFacilityIds"]),
            {
                self.hf_1.id,
                self.hf_2.id,
                self.hf_3.id,
                self.hf_4.id,
            },
        )

    def test_removes_district_when_all_its_hfs_are_assigned(self):
        mission = self.create_mission(
            "MISSION002",
            date(2026, 1, 5),
            date(2026, 1, 25),
        )

        self.assign_district(mission, self.district_4)
        self.assign_hf(mission, self.hf_1)
        self.assign_hf(mission, self.hf_2)

        result = self.execute_available_districts_query()
        data = result.data

        self.assertIsNone(result.errors)

        data = result.data["checkMissionAvailability"]

        self.assertEqual(data["districtIds"], [self.district_5.id])

        self.assertEqual(
            set(data["healthFacilityIds"]),
            {self.hf_3.id, self.hf_4.id},
        )

    def test_keeps_district_when_at_least_one_hf_is_available(self):
        """
        Si une seule FOSA reste disponible,
        le district doit être conservé avec cette FOSA.
        """
        mission = self.create_mission(
            "MISSION003",
            date(2026, 1, 5),
            date(2026, 1, 25),
        )

        self.assign_hf(mission, self.hf_1)

        result = self.execute_available_districts_query()
        data = result.data["checkMissionAvailability"]

        self.assertIn(
            self.district_4.id,
            data["district_ids"],
        )

        self.assertIn(self.hf_2.id, result.health_facility_ids)
        self.assertNotIn(self.hf_1.id, result.health_facility_ids)

    def test_ignores_missions_outside_requested_period(self):
        """
        Une mission terminée avant la période demandée
        ne doit pas empêcher l'éligibilité.
        """
        mission = self.create_mission(
            "MISSION004",
            date(2025, 11, 1),
            date(2025, 12, 31),
        )

        self.assign_district(mission, self.district_4)
        self.assign_hf(mission, self.hf_1)

        result = self.execute_available_districts_query()
        data = result.data["checkMissionAvailability"]

        self.assertIn(
            self.district_4.id,
            data["district_ids"],
        )
        self.assertIn(self.hf_1.id, data["health_facility_ids"])

    def test_includes_missions_that_overlap_requested_period(self):
        """
        Une mission qui commence avant la période demandée
        mais se termine pendant celle-ci doit être prise en compte.
        """
        mission = self.create_mission(
            "MISSION005",
            date(2025, 12, 20),
            date(2026, 1, 10),
        )

        self.assign_district(mission, self.district_4)
        self.assign_hf(mission, self.hf_1)

        result = self.execute_available_districts_query()
        data = result.data["checkMissionAvailability"]

        self.assertNotIn(
            self.district_4.id,
            data["district_ids"],
        )
        self.assertNotIn(self.hf_1.id, data["health_facility_ids"])

    def test_raises_permission_denied_without_permission(self):
        self.user.has_perms = lambda perms: False

        with self.assertRaises(PermissionDenied):
            self.execute_available_districts_query()
