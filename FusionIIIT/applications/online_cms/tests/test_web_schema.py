"""
test_web_schema.py — Automated HTML Session-Auth view validation.

Uses WEB_SCHEMA registry to test every Django HTML view for:
  1. NEGATIVE: Unauthenticated request is redirected to login (302).
  2. POSITIVE: Authenticated request returns the expected HTTP status
               (200 for rendered pages, 302 for redirect-on-success POSTs).

Add every new HTML view here — no separate test function needed.
"""

from rest_framework import status
from .base_setup import FusionBaseTestCase

# ─────────────────────────────────────────────────────────────────────────────
# Schema registry — one dict per HTML view
# ─────────────────────────────────────────────────────────────────────────────
# Keys:
#   name                  Human-readable label
#   url                   Absolute path (no domain)
#   method                "GET" or "POST"
#   role_required         "student" | "faculty" | "admin"
#   payload               dict for POST, None for GET
#   expected_success_code HTTP status returned on authenticated success

WEB_SCHEMA = [
    # ── Dashboard / course list ───────────────────────────────────────────────
    {
        "name":                  "View registered courses (student)",
        "url":                   "/online_cms/",
        "method":                "GET",
        "role_required":         "student",
        "payload":               None,
        "expected_success_code": status.HTTP_200_OK,
    },
    {
        "name":                  "View course detail page (student)",
        "url":                   "/online_cms/CS101/1.0/",
        "method":                "GET",
        "role_required":         "student",
        "payload":               None,
        "expected_success_code": status.HTTP_200_OK,
    },

    # ── Forum ─────────────────────────────────────────────────────────────────
    {
        "name":                  "View course forum (student)",
        "url":                   "/online_cms/CS101/1.0/forum",
        "method":                "GET",
        "role_required":         "student",
        "payload":               None,
        "expected_success_code": status.HTTP_200_OK,
    },
    {
        "name":                  "Post new forum comment (student)",
        "url":                   "/online_cms/CS101/1.0/ajax_new",
        "method":                "POST",
        "role_required":         "student",
        "payload":               {"comment": "Web schema test question"},
        "expected_success_code": status.HTTP_200_OK,
    },
    {
        "name":                  "Reply to forum post (faculty)",
        "url":                   "/online_cms/CS101/1.0/ajax_reply",
        "method":                "POST",
        "role_required":         "faculty",
        "payload":               {"comment": "Web schema test reply", "comment_id": "1"},
        "expected_success_code": status.HTTP_200_OK,
    },

    # ── Faculty: content management ───────────────────────────────────────────
    {
        "name":                  "Faculty adds module",
        "url":                   "/online_cms/CS101/1.0/add_modules",
        "method":                "POST",
        "role_required":         "faculty",
        "payload":               {"module_name": "Web Schema Module"},
        "expected_success_code": status.HTTP_302_FOUND,
    },
    {
        "name":                  "Faculty adds document",
        "url":                   "/online_cms/CS101/1.0/add_documents",
        "method":                "POST",
        "role_required":         "faculty",
        "payload": {
            "module_id":     "1",
            "description":   "Web schema doc",
            "document_name": "WS_Doc.pdf",
        },
        "expected_success_code": status.HTTP_302_FOUND,
    },
    {
        "name":                  "Faculty adds assignment",
        "url":                   "/online_cms/CS101/1.0/add_assignment",
        "method":                "POST",
        "role_required":         "faculty",
        "payload": {
            "assignment_name": "WS_Assignment",
            "submit_date":     "2025-12-20 23:59",
        },
        "expected_success_code": status.HTTP_302_FOUND,
    },

    # ── Quiz views ────────────────────────────────────────────────────────────
    {
        "name":                  "Faculty accesses create quiz page",
        "url":                   "/online_cms/CS101/create_quiz/",
        "method":                "GET",
        "role_required":         "faculty",
        "payload":               None,
        "expected_success_code": status.HTTP_200_OK,
    },
    {
        "name":                  "Student accesses quiz page",
        "url":                   "/online_cms/quiz/1/",
        "method":                "GET",
        "role_required":         "student",
        "payload":               None,
        "expected_success_code": status.HTTP_200_OK,
    },

    # ── Grading ───────────────────────────────────────────────────────────────
    {
        "name":                  "Faculty creates grading scheme (web)",
        "url":                   "/online_cms/CS101/1.0/create_grading_scheme",
        "method":                "POST",
        "role_required":         "faculty",
        "payload": {
            "type_of_evaluation": "EndSem",
            "weightage":          40,
        },
        "expected_success_code": status.HTTP_302_FOUND,
    },

    # ── Attendance ────────────────────────────────────────────────────────────
    {
        "name":                  "Faculty submits attendance sheet",
        "url":                   "/online_cms/CS101/1.0/attendance",
        "method":                "POST",
        "role_required":         "faculty",
        "payload":               {"date": "2025-11-05"},
        "expected_success_code": status.HTTP_302_FOUND,
    },
    {
        "name":                  "Faculty accesses add_attendance page",
        "url":                   "/online_cms/CS101/1.0/add_attendance",
        "method":                "GET",
        "role_required":         "faculty",
        "payload":               None,
        "expected_success_code": status.HTTP_200_OK,
    },

    # ── Delete content ────────────────────────────────────────────────────────
    {
        "name":                  "Faculty deletes content item",
        "url":                   "/online_cms/CS101/1.0/delete/",
        "method":                "POST",
        "role_required":         "faculty",
        "payload":               {"item_id": "1", "item_type": "document"},
        "expected_success_code": status.HTTP_302_FOUND,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Test class
# ─────────────────────────────────────────────────────────────────────────────

class WebSchemaValidationTests(FusionBaseTestCase):
    """
    Dynamically validates every view in WEB_SCHEMA.

    For each entry two sub-tests run automatically:
      • Negative — unauthenticated request must redirect to login (302).
      • Positive — session-authenticated request must return
                   expected_success_code.
    """

    def test_views_against_schema(self):
        for view in WEB_SCHEMA:
            with self.subTest(view=view["name"]):

                # ── Test 1 (Negative): Unauthenticated → redirect to login ────
                self.clear_auth()
                if view["method"] == "GET":
                    res_unauth = self.client.get(view["url"])
                else:
                    res_unauth = self.client.post(
                        view["url"], data=view["payload"]
                    )

                self.assertEqual(
                    res_unauth.status_code,
                    status.HTTP_302_FOUND,
                    msg=(
                        f"[{view['name']}] Expected unauthenticated request "
                        f"to redirect (302), got {res_unauth.status_code}"
                    )
                )
                # Must redirect toward login page, not some other URL
                self.assertIn(
                    '/login',
                    res_unauth.get('Location', ''),
                    msg=(
                        f"[{view['name']}] Redirect target does not appear "
                        f"to be a login page: {res_unauth.get('Location')}"
                    )
                )

                # ── Test 2 (Positive): Authenticated → expected status ─────────
                self.auth_session(role=view["role_required"])
                if view["method"] == "GET":
                    res_auth = self.client.get(view["url"])
                else:
                    res_auth = self.client.post(
                        view["url"], data=view["payload"]
                    )

                self.assertEqual(
                    res_auth.status_code,
                    view["expected_success_code"],
                    msg=(
                        f"[{view['name']}] Expected "
                        f"{view['expected_success_code']}, "
                        f"got {res_auth.status_code}"
                    )
                )
                # Clean up session for next iteration
                self.logout_session()
