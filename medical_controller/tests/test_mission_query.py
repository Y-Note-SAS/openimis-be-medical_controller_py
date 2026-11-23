from datetime import date
from unittest.mock import patch
from types import SimpleNamespace
import uuid
import graphene
from graphene.relay import Node
from django.test import TestCase
from location.test_helpers import create_test_location
from core.test_helpers import create_test_interactive_user
from medical_controller.schema import Query
from medical_controller.models import MedicalControlMission, MissionDistricts


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
            mission_date="2026-01-31",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
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
                                districts {
                                    edges {
                                        node {
                                            district {
                                                edges {
                                                    node {
                                                        name
                                                    }
                                                }
                                            }
                                        }
                                    }
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

            print("result data 11", result.data)
            print("result errors 11 ", result.errors)

            self.assertEqual(
                len(result.data["missionsDistricts"]["edges"]),
                1,
            )
            self.assertEqual(
                result.data["missionsDistricts"]["edges"][0]["node"]\
                    ["districts"]["edges"][0]["node"]["district"]["name"],
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
                                            code
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

            print("result data 0 ", result.data)
            print("result errors 0 ", result.errors)

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
