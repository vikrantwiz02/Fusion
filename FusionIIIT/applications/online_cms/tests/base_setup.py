"""
base_setup.py — Core utilities for the online_cms test suite.

Provides FusionBaseTestCase with:
  - Standard university roles: student, faculty, admin
  - DRF Token authentication helpers
  - Django Session authentication helpers
"""

from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class FusionBaseTestCase(APITestCase):
    """
    Universal base class for all online_cms tests.
    Inherits from APITestCase so both self.client (DRF APIClient)
    and session-based login are available.
    """

    def setUp(self):
        """Initializes standard test users representing every ERP role."""

        # ── 1. Create Users ───────────────────────────────────────────────────
        self.student_user = User.objects.create_user(
            username='23BCS265',
            password='testpassword123',
            email='student@iiitdmj.ac.in'
        )
        self.faculty_user = User.objects.create_user(
            username='faculty_cs',
            password='testpassword123',
            email='faculty@iiitdmj.ac.in'
        )
        self.admin_user = User.objects.create_superuser(
            username='erp_admin',
            password='testpassword123',
            email='admin@iiitdmj.ac.in'
        )

        # ── 2. Generate DRF Tokens ────────────────────────────────────────────
        self.student_token = Token.objects.create(user=self.student_user)
        self.faculty_token = Token.objects.create(user=self.faculty_user)
        # Admin token is generated on demand via auth_token(role='admin')
        self.admin_token = Token.objects.create(user=self.admin_user)

    # ── Session Auth (HTML views) ─────────────────────────────────────────────

    def auth_session(self, role: str = "student"):
        """
        Logs in the Django test client for session-authenticated HTML views.

        Args:
            role: One of "student", "faculty", or "admin".
        """
        credentials = {
            "student": ("23BCS265",   "testpassword123"),
            "faculty": ("faculty_cs", "testpassword123"),
            "admin":   ("erp_admin",  "testpassword123"),
        }
        username, password = credentials[role]
        self.client.login(username=username, password=password)

    def logout_session(self):
        """Clears the session so the client is unauthenticated."""
        self.client.logout()

    # ── Token Auth (API endpoints) ────────────────────────────────────────────

    def auth_token(self, role: str = "student"):
        """
        Sets the DRF Bearer Token credential for JSON API endpoints.

        Args:
            role: One of "student", "faculty", or "admin".
        """
        token_map = {
            "student": self.student_token.key,
            "faculty": self.faculty_token.key,
            "admin":   self.admin_token.key,
        }
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + token_map[role]
        )

    def clear_auth(self):
        """Removes all auth credentials — used to simulate an anonymous user."""
        self.client.credentials()
        self.client.logout()
