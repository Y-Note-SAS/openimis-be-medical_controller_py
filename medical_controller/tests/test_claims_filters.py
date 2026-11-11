from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase

from claim.models import Claim
from claim.test_helpers import create_test_claim, create_test_claimservice
from core.test_helpers import create_test_interactive_user
from location.models import Location
from medical.test_helpers import create_test_service

from medical_controller.models import (
    FilteredClaimsForMission,
    MedicalControlMission,
)
from medical_controller.schema import (
    ClaimsForHealthFacilitiesResultGQLType,
    Query,
)


class ClaimsForHealthFacilitiesFiltersTest(TestCase):
    """Tests du filtre `services` et du tri sur claimsForHealthFacilities."""

    def setUp(self):
        self.user = create_test_interactive_user()

        self.region = Location.objects.create(code="T38511-R", name="East")
        self.district = Location.objects.create(code="T38511-D", name="District")

        self.mission = MedicalControlMission(
            mission_code="T38511",
            region=self.region,
            district=self.district,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            status=MedicalControlMission.STATUS_IN_PROGRESS,
            user=self.user,
        )
        self.mission.save(username=self.user.username)

        self.cpn1 = create_test_service("S", custom_props={"code": "T38511-CPN1"})
        self.cpn2 = create_test_service("S", custom_props={"code": "T38511-CPN2"})

        self.claim_early = create_test_claim(custom_props={"date_to": date(2026, 1, 5)})
        self.claim_late = create_test_claim(custom_props={"date_to": date(2026, 1, 20)})

        # claim_early porte deux fois CPN1 (doit rester une seule ligne apres filtre)
        create_test_claimservice(self.claim_early, custom_props={"service": self.cpn1})
        create_test_claimservice(self.claim_early, custom_props={"service": self.cpn1})
        create_test_claimservice(self.claim_late, custom_props={"service": self.cpn2})

        self.filtered_early = self._filter(self.claim_early, "1", audited=False)
        self.filtered_late = self._filter(self.claim_late, "1", audited=False)

        class Info:
            pass

        self.info = Info()
        self.info.context = SimpleNamespace(user=self.user)

    def _filter(self, claim, category, audited):
        obj = FilteredClaimsForMission(
            id=uuid4(),
            mission=self.mission,
            claim=claim,
            claim_category=category,
            audited=audited,
            from_rejected_to_valuated=False,
            user_created=self.user,
            user_updated=self.user,
        )
        obj.save(username=self.user.username)
        return obj

    def _resolve(self, **kwargs):
        return Query().resolve_claims_for_health_facilities(
            self.info,
            health_facility_ids=[
                self.claim_early.health_facility_id,
                self.claim_late.health_facility_id,
            ],
            mission_code=self.mission.mission_code,
            **kwargs,
        )

    def test_services_argument_is_exposed(self):
        self.assertIn(
            "services",
            Query.claims_for_health_facilities.args,
        )

    def test_order_by_argument_is_exposed(self):
        self.assertIn(
            "orderBy",
            ClaimsForHealthFacilitiesResultGQLType.claims.args,
        )

    def test_services_filter_returns_only_matching_claims(self):
        with patch.object(self.user, "has_perms", return_value=True):
            result = self._resolve(category="1", services=["T38511-CPN1"])

        claim_ids = list(result.claims.values_list("claim_id", flat=True))
        self.assertEqual(claim_ids, [self.claim_early.id])

    def test_services_filter_does_not_duplicate_rows(self):
        with patch.object(self.user, "has_perms", return_value=True):
            result = self._resolve(category="1", services=["T38511-CPN1"])

        # deux ClaimService CPN1 sur le meme claim -> une seule ligne
        self.assertEqual(result.claims.count(), 1)

    def test_default_order_is_chronological(self):
        with patch.object(self.user, "has_perms", return_value=True):
            result = self._resolve(category="1")

        dates = list(result.claims.values_list("claim__date_to", flat=True))
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(
            list(result.claims.values_list("claim_id", flat=True)),
            [self.claim_early.id, self.claim_late.id],
        )

    def test_all_audited_ignores_filters(self):
        # un claim d'une autre categorie n'est pas audite -> all_audited False
        other = create_test_claim(custom_props={"date_to": date(2026, 1, 10)})
        self._filter(other, "2", audited=False)

        with patch.object(self.user, "has_perms", return_value=True):
            result = self._resolve(category="1")

        self.assertFalse(result.all_audited)

    def test_all_audited_true_when_every_claim_is_audited(self):
        self.filtered_early.audited = True
        self.filtered_early.save(username=self.user.username)
        self.filtered_late.audited = True
        self.filtered_late.save(username=self.user.username)
        Claim.objects.filter(
            id__in=[self.claim_early.id, self.claim_late.id]
        ).update(audited=True)

        with patch.object(self.user, "has_perms", return_value=True):
            result = self._resolve(category="1")

        self.assertTrue(result.all_audited)
