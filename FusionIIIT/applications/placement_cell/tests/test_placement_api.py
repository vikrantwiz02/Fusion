"""
Self-contained regression/contract tests for the placement_cell API module.

Goals (kept deliberately robust so they keep passing in the future):
  * Schema regressions  - guard the data-model fixes (e.g. Education.grade width).
  * URL wiring          - every placement API route resolves to a real view and
                          the urlconf stays API-only (no legacy template routes).
  * Authentication      - protected endpoints reject anonymous callers.
  * Authorization       - officer-only (TPO) endpoints reject students and admit
                          placement officers.

Run with the dedicated test settings (migrations disabled so the historical
migration chain cannot block test-DB creation)::

    python manage.py test applications.placement_cell.tests.test_placement_api \
        --settings=test_settings
"""

import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from applications.academic_information.models import Student
from applications.globals.models import (
    DepartmentInfo,
    Designation,
    ExtraInfo,
    HoldsDesignation,
)
from applications.placement_cell.api import urls as placement_urls
from applications.placement_cell.models import (
    Education,
    NotifyStudent,
    PlacementRestriction,
    PlacementSchedule,
)


class PlacementBaseTest(TestCase):
    """Builds a department, a student, a placement officer and a plain user."""

    def setUp(self):
        self.department = DepartmentInfo.objects.create(name="CSE")
        self.student_designation = Designation.objects.create(
            name="student", full_name="Student"
        )
        self.officer_designation = Designation.objects.create(
            name="placement officer", full_name="Placement Officer"
        )

        self.student_user = self._make_user("student1", "2023001", user_type="student")
        Student.objects.create(
            id=ExtraInfo.objects.get(user=self.student_user),
            programme="B.Tech",
            batch=2026,
            cpi=8.5,
            category="GEN",
        )
        self._hold(self.student_user, self.student_designation)

        self.officer_user = self._make_user("officer1", "OFF001", user_type="staff")
        self._hold(self.officer_user, self.officer_designation)

        # Authenticated but holds no placement designation.
        self.plain_user = self._make_user("plain1", "PLN001", user_type="staff")

    # -- fixture helpers -----------------------------------------------------
    def _make_user(self, username, info_id, *, user_type):
        user = User.objects.create_user(
            username=username,
            password="pw",
            email="{}@example.com".format(username),
            first_name=username,
        )
        extra, _ = ExtraInfo.objects.get_or_create(
            user=user,
            defaults={"id": info_id, "user_type": user_type, "department": self.department},
        )
        extra.user_type = user_type
        extra.department = self.department
        extra.save(update_fields=["user_type", "department"])
        return user

    def _hold(self, user, designation):
        HoldsDesignation.objects.create(
            user=user, working=user, designation=designation
        )

    def _client(self, user=None):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user=user)
        return client


class SchemaRegressionTests(PlacementBaseTest):
    def test_grade_field_is_wide_enough_for_cgpa(self):
        # A previous migration shrank grade to 3 chars and truncated real CGPA
        # data (e.g. "8.39"). Keep it wide enough forever.
        self.assertGreaterEqual(Education._meta.get_field("grade").max_length, 4)

    def test_education_persists_cgpa_value(self):
        student = Student.objects.get(id__user=self.student_user)
        edu = Education.objects.create(
            unique_id=student, degree="B.Tech", grade="8.39", institute="IIITDMJ"
        )
        edu.refresh_from_db()
        self.assertEqual(edu.grade, "8.39")

    def test_core_models_are_creatable(self):
        notify = NotifyStudent.objects.create(
            placement_type="PLACEMENT",
            company_name="Acme Corp",
            ctc=Decimal("12.50"),
            description="Campus drive",
        )
        schedule = PlacementSchedule.objects.create(
            notify_id=notify,
            title="Acme Corp",
            placement_date=datetime.date.today(),
            location="Campus",
            time=datetime.time(10, 0),
        )
        self.assertIsNotNone(schedule.pk)


class UrlWiringTests(PlacementBaseTest):
    def test_every_route_resolves_to_a_callable_view(self):
        self.assertTrue(placement_urls.urlpatterns)
        for pattern in placement_urls.urlpatterns:
            self.assertTrue(
                callable(pattern.callback),
                "URL {!r} does not resolve to a view".format(pattern.name),
            )

    def test_urlconf_is_api_only_no_legacy_template_routes(self):
        # The legacy template-based routes were removed; guard against their
        # reintroduction by requiring every route to live under ^api/.
        for pattern in placement_urls.urlpatterns:
            regex = pattern.pattern.regex.pattern
            self.assertTrue(
                regex.startswith("^api/"),
                "Unexpected non-API route present: {}".format(regex),
            )

    def test_key_routes_reverse(self):
        for name in [
            "placement_api",
            "placement_statistics_api",
            "calendar_api",
            "debarred_students_api",
            "restrictions_api",
            "generate_cv_api",
        ]:
            self.assertTrue(reverse("placement:{}".format(name)))


class AuthenticationTests(PlacementBaseTest):
    PROTECTED = [
        "placement_api",
        "placement_statistics_api",
        "calendar_api",
        "debarred_students_api",
        "restrictions_api",
        "my_applications_api",
    ]

    def test_protected_endpoints_reject_anonymous(self):
        client = APIClient()
        for name in self.PROTECTED:
            response = client.get(reverse("placement:{}".format(name)))
            self.assertIn(
                response.status_code,
                (401, 403),
                "{} should require authentication (got {})".format(
                    name, response.status_code
                ),
            )


class AuthorizationTests(PlacementBaseTest):
    OFFICER_ONLY = ["debarred_students_api", "restrictions_api"]

    def test_students_are_denied_officer_endpoints(self):
        client = self._client(self.student_user)
        for name in self.OFFICER_ONLY:
            response = client.get(reverse("placement:{}".format(name)))
            self.assertEqual(
                response.status_code,
                403,
                "{} should be forbidden for students".format(name),
            )

    def test_plain_authenticated_user_denied_officer_endpoints(self):
        client = self._client(self.plain_user)
        for name in self.OFFICER_ONLY:
            response = client.get(reverse("placement:{}".format(name)))
            self.assertEqual(response.status_code, 403)

    def test_officer_can_read_officer_endpoints(self):
        client = self._client(self.officer_user)
        for name in self.OFFICER_ONLY:
            response = client.get(reverse("placement:{}".format(name)))
            self.assertEqual(
                response.status_code,
                200,
                "{} should be allowed for officers".format(name),
            )

    def test_officer_can_list_placements(self):
        response = self._client(self.officer_user).get(
            reverse("placement:placement_api")
        )
        self.assertEqual(response.status_code, 200)

    def test_officer_can_create_and_list_restriction(self):
        client = self._client(self.officer_user)
        create = client.post(
            reverse("placement:restrictions_api"),
            data={
                "criteria": "CPI",
                "condition": "lt",
                "value": "6.0",
                "description": "Low CPI",
            },
            format="json",
        )
        self.assertEqual(create.status_code, 201)
        self.assertEqual(PlacementRestriction.objects.count(), 1)

        listed = client.get(reverse("placement:restrictions_api"))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
