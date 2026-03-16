"""
test_api_schema.py — Automated DRF Token-Auth endpoint validation.

Uses a schema registry (API_SCHEMA) to loop dynamically over every
JSON API endpoint and verify:
  1. NEGATIVE: Unauthenticated requests receive HTTP 401 UNAUTHORIZED.
  2. POSITIVE: Authenticated requests receive the expected success code.

Add every new API endpoint to API_SCHEMA — no separate test function needed.
"""

from rest_framework import status
from .base_setup import FusionBaseTestCase

# ─────────────────────────────────────────────────────────────────────────────
# Schema registry — one dict per API endpoint
# ─────────────────────────────────────────────────────────────────────────────
# Keys:
#   name                  Human-readable label (used in subTest output)
#   url                   Absolute path (no domain)
#   method                "GET" or "POST"
#   role_required         "student" | "faculty" | "admin"
#   payload               dict for POST requests, None for GET
#   expected_success_code HTTP status code on authenticated success

API_SCHEMA = [
    # ── Course listing ────────────────────────────────────────────────────────
    {
        "name":                 "List all courses (API)",
        "url":                  "/online_cms/api/courses",
        "method":               "GET",
        "role_required":        "student",
        "payload":              None,
        "expected_success_code": status.HTTP_200_OK,
    },

    # ── Course detail ─────────────────────────────────────────────────────────
    # Note: actual course_code/version are substituted at test time via
    # setUp; the URL below uses a seeded value from CoursesFactory.
    {
        "name":                 "Get course detail by code+version (API)",
        "url":                  "/online_cms/api/CS101/1.0/",
        "method":               "GET",
        "role_required":        "student",
        "payload":              None,
        "expected_success_code": status.HTTP_200_OK,
    },

    # ── Assignment creation (faculty) ─────────────────────────────────────────
    {
        "name":                 "Faculty creates assignment",
        "url":                  "/online_cms/CS101/1.0/add_assignment",
        "method":               "POST",
        "role_required":        "faculty",
        "payload": {
            "assignment_name": "Lab_Report_Schema_Test",
            "submit_date":     "2025-12-15 23:59",
        },
        "expected_success_code": status.HTTP_302_FOUND,   # view redirects on success
    },

    # ── Student submits assignment ────────────────────────────────────────────
    # File upload is handled separately in workflow tests; this checks auth gate.
    {
        "name":                 "Student upload_assignment auth gate",
        "url":                  "/online_cms/CS101/1.0/upload_assignment",
        "method":               "POST",
        "role_required":        "student",
        "payload": {
            "assignment_topic": "1",
            "name":             "my_solution",
        },
        "expected_success_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        # 422 because file is missing — proves auth passed but validation failed
    },

    # ── Forum: add new post ───────────────────────────────────────────────────
    {
        "name":                 "Student posts forum question",
        "url":                  "/online_cms/CS101/1.0/ajax_new",
        "method":               "POST",
        "role_required":        "student",
        "payload":              {"comment": "Schema test question"},
        "expected_success_code": status.HTTP_200_OK,
    },

    # ── Add module (faculty) ──────────────────────────────────────────────────
    {
        "name":                 "Faculty adds course module",
        "url":                  "/online_cms/CS101/1.0/add_modules",
        "method":               "POST",
        "role_required":        "faculty",
        "payload":              {"module_name": "Schema Test Module"},
        "expected_success_code": status.HTTP_302_FOUND,
    },

    # ── Add document (faculty) ────────────────────────────────────────────────
    {
        "name":                 "Faculty uploads course document",
        "url":                  "/online_cms/CS101/1.0/add_documents",
        "method":               "POST",
        "role_required":        "faculty",
        "payload": {
            "module_id":     "1",
            "description":   "Schema doc",
            "document_name": "Schema.pdf",
        },
        "expected_success_code": status.HTTP_302_FOUND,
    },

    # ── Grading scheme ────────────────────────────────────────────────────────
    {
        "name":                 "Faculty creates grading scheme",
        "url":                  "/online_cms/CS101/1.0/create_grading_scheme",
        "method":               "POST",
        "role_required":        "faculty",
        "payload": {
            "type_of_evaluation": "Quiz",
            "weightage":          20,
        },
        "expected_success_code": status.HTTP_302_FOUND,
    },

    # ── Create quiz (faculty) ─────────────────────────────────────────────────
    {
        "name":                 "Faculty creates quiz",
        "url":                  "/online_cms/CS101/create_quiz/",
        "method":               "POST",
        "role_required":        "faculty",
        "payload": {
            "quiz_name":           "Schema Quiz",
            "start_time":          "2025-11-01 10:00",
            "end_time":            "2025-11-01 11:00",
            "d_day":               "0",
            "d_hour":              "1",
            "d_minute":            "0",
            "negative_marks":      0.25,
            "number_of_question":  5,
            "description":         "Test quiz",
            "rules":               "No cheating",
            "total_score":         10,
        },
        "expected_success_code": status.HTTP_302_FOUND,
    },

    # ── Create question bank (faculty) ────────────────────────────────────────
    {
        "name":                 "Faculty creates question bank",
        "url":                  "/online_cms/CS101/create_bank",
        "method":               "POST",
        "role_required":        "faculty",
        "payload":              {"name": "Schema QB"},
        "expected_success_code": status.HTTP_302_FOUND,
    },

    # ── Attendance submit ─────────────────────────────────────────────────────
    {
        "name":                 "Faculty submits attendance",
        "url":                  "/online_cms/CS101/1.0/attendance",
        "method":               "POST",
        "role_required":        "faculty",
        "payload":              {"date": "2025-11-01"},
        "expected_success_code": status.HTTP_302_FOUND,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Test class
# ─────────────────────────────────────────────────────────────────────────────

class APISchemaValidationTests(FusionBaseTestCase):
    """
    Dynamically validates every endpoint in API_SCHEMA.

    For each entry two sub-tests run automatically:
      • Negative — unauthenticated request must return 401 or redirect to login.
      • Positive — authenticated request must return expected_success_code.
    """

    def test_endpoints_against_schema(self):
        for endpoint in API_SCHEMA:
            with self.subTest(endpoint=endpoint["name"]):

                # ── Test 1 (Negative): Unauthorised access blocked ────────────
                self.clear_auth()
                if endpoint["method"] == "GET":
                    res_unauth = self.client.get(endpoint["url"])
                else:
                    res_unauth = self.client.post(
                        endpoint["url"], data=endpoint["payload"]
                    )

                unauth_codes = [
                    status.HTTP_401_UNAUTHORIZED,
                    status.HTTP_403_FORBIDDEN,
                    status.HTTP_302_FOUND,   # session login redirect
                ]
                self.assertIn(
                    res_unauth.status_code,
                    unauth_codes,
                    msg=(
                        f"[{endpoint['name']}] Expected unauthenticated request "
                        f"to be blocked, got {res_unauth.status_code}"
                    )
                )

                # ── Test 2 (Positive): Authorised access succeeds ─────────────
                self.auth_token(role=endpoint["role_required"])
                if endpoint["method"] == "GET":
                    res_auth = self.client.get(endpoint["url"])
                else:
                    res_auth = self.client.post(
                        endpoint["url"], data=endpoint["payload"]
                    )

                self.assertEqual(
                    res_auth.status_code,
                    endpoint["expected_success_code"],
                    msg=(
                        f"[{endpoint['name']}] Expected "
                        f"{endpoint['expected_success_code']}, "
                        f"got {res_auth.status_code}"
                    )
                )
