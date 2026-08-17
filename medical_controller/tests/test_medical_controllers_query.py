from unittest.mock import patch

from django.test import TestCase

from medical_controller.schema import Query
from core.test_helpers import create_test_interactive_user


class MedicalControllersQueryTest(TestCase):

    def setUp(self):
        self.user = create_test_interactive_user()

        class Context:
            pass

        self.context = Context()
        self.context.user = self.user

        class Info:
            pass

        self.info = Info()
        self.info.context = self.context

    def test_returns_queryset(self):
        """
        Le resolver doit retourner un QuerySet.
        """

        with patch.object(
            self.user,
            "has_perms",
            return_value=True,
        ):
            result = Query().resolve_medical_controllers(
                self.info,
            )

        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, "filter"))
        self.assertTrue(hasattr(result, "distinct"))

    def test_returns_distinct_queryset(self):
        """
        Le queryset doit être distinct afin d'éviter les doublons
        provoqués par les jointures user_roles -> rights.
        """

        with patch.object(
            self.user,
            "has_perms",
            return_value=True,
        ):
            result = Query().resolve_medical_controllers(
                self.info,
            )

        self.assertTrue(result.query.distinct)

    def test_unauthorized_user_is_rejected(self):
        """
        Un utilisateur sans permission ne doit pas accéder
        à la liste des medical controllers.
        """

        from django.core.exceptions import PermissionDenied

        with patch.object(
            self.user,
            "has_perms",
            return_value=False,
        ):
            with self.assertRaises(PermissionDenied):
                Query().resolve_medical_controllers(
                    self.info,
                )
