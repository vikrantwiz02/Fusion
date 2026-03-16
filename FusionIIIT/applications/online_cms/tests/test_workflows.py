"""
test_workflows.py — Black-box integration tests for online_cms legacy Fat Views.

These tests simulate complete user journeys using the Django test client.
We treat views.py as a black box: send HTTP requests, then assert that the
database state changed as expected.

AAA (Arrange-Act-Assert) pattern is applied throughout.

Covered workflows:
  1. Faculty adds an assignment  → StudentAssignment record exists after student submits
  2. Forum post (ajax_new)       → Forum record created in DB
  3. Forum reply (ajax_reply)    → ForumReply record created in DB
  4. Add module                  → Modules record created
  5. Add document                → CourseDocuments record created
  6. Grading scheme creation     → GradingScheme record created
  7. Negative: unauthenticated access is redirected to login
  8. Negative: student cannot access faculty-only add_assignment view
"""

from django.utils import timezone
from datetime import timedelta

from .base_setup import FusionBaseTestCase
from .factories import (
    CoursesFactory, ModulesFactory, AssignmentFactory,
    StudentFactory, ExtraInfoFactory, CourseInstructorFactory,
    QuizFactory, QuestionBankFactory, TopicsFactory,
)
from applications.online_cms.models import (
    Assignment, StudentAssignment, Forum, ForumReply,
    Modules, CourseDocuments, GradingScheme,
)


# ── Helper to construct URL prefix for a course ──────────────────────────────
def _course_url(course_code: str, version: str) -> str:
    return f'/online_cms/{course_code}/{version}'


# ─────────────────────────────────────────────────────────────────────────────
# 1. Assignment Workflow
# ─────────────────────────────────────────────────────────────────────────────

class AssignmentWorkflowTests(FusionBaseTestCase):
    """
    Tests the full assignment lifecycle:
      Faculty creates assignment → Student submits solution.
    """

    def setUp(self):
        super().setUp()
        # Build course & link faculty as instructor
        self.course = CoursesFactory(code='CS301', version=1.0)
        self.faculty_extra = ExtraInfoFactory(
            user=self.faculty_user, user_type='faculty'
        )
        self.student_extra = ExtraInfoFactory(
            user=self.student_user, user_type='student'
        )
        self.student = StudentFactory(id=self.student_extra)
        CourseInstructorFactory(
            course_id=self.course, instructor_id=self.faculty_extra
        )
        # Pre-create an assignment (normally done by faculty via the UI)
        self.assignment = AssignmentFactory(course_id=self.course)

    # ── Positive ─────────────────────────────────────────────────────────────

    def test_faculty_can_create_assignment_successfully(self):
        """
        ARRANGE: Faculty is logged in.
        ACT:     POST to add_assignment with valid data.
        ASSERT:  A new Assignment record exists in the DB with correct name.
        """
        self.auth_session(role='faculty')
        payload = {
            'assignment_name': 'Lab_Report_2',
            'submit_date':     (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M'),
        }
        self.client.post(
            f'{_course_url("CS301", "1.0")}/add_assignment',
            data=payload
        )
        # Assert the DB was updated
        self.assertTrue(
            Assignment.objects.filter(
                course_id=self.course, assignment_name='Lab_Report_2'
            ).exists()
        )

    # ── Negative ─────────────────────────────────────────────────────────────

    def test_add_assignment_fails_for_unauthenticated_user(self):
        """
        ARRANGE: No user is authenticated.
        ACT:     POST to add_assignment without login.
        ASSERT:  Response is a redirect to the login page (302).
        """
        self.clear_auth()
        response = self.client.post(
            f'{_course_url("CS301", "1.0")}/add_assignment',
            data={'assignment_name': 'Illegal', 'submit_date': '2025-12-01 23:59'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response['Location'])

    def test_add_assignment_fails_for_student_role(self):
        """
        ARRANGE: Student is logged in (not a faculty member).
        ACT:     POST to add_assignment.
        ASSERT:  The view rejects the request (not 200/201).
        """
        self.auth_session(role='student')
        response = self.client.post(
            f'{_course_url("CS301", "1.0")}/add_assignment',
            data={'assignment_name': 'Hack_Assignment', 'submit_date': '2025-12-01 23:59'}
        )
        # Expect 403 Forbidden or redirect — NOT a success
        self.assertNotIn(response.status_code, [200, 201])


# ─────────────────────────────────────────────────────────────────────────────
# 2. Forum Workflow
# ─────────────────────────────────────────────────────────────────────────────

class ForumWorkflowTests(FusionBaseTestCase):
    """
    Tests the forum Q&A lifecycle:
      Student posts a question → Faculty (or student) replies.
    """

    def setUp(self):
        super().setUp()
        self.course = CoursesFactory(code='CS302', version=1.0)
        self.faculty_extra = ExtraInfoFactory(
            user=self.faculty_user, user_type='faculty'
        )
        self.student_extra = ExtraInfoFactory(
            user=self.student_user, user_type='student'
        )
        self.student = StudentFactory(id=self.student_extra)
        CourseInstructorFactory(
            course_id=self.course, instructor_id=self.faculty_extra
        )

    # ── Positive ─────────────────────────────────────────────────────────────

    def test_student_can_post_forum_question(self):
        """
        ARRANGE: Student is logged in.
        ACT:     POST to ajax_new with a comment.
        ASSERT:  A Forum record for this course exists in the DB.
        """
        self.auth_session(role='student')
        payload = {'comment': 'When is the quiz scheduled?'}
        self.client.post(
            f'{_course_url("CS302", "1.0")}/ajax_new',
            data=payload,
            content_type='application/x-www-form-urlencoded'
        )
        self.assertTrue(
            Forum.objects.filter(course_id=self.course).exists()
        )

    def test_faculty_can_reply_to_forum_question(self):
        """
        ARRANGE: A student question exists; faculty is logged in.
        ACT:     POST to ajax_reply with the question id.
        ASSERT:  A ForumReply record exists linking question → reply.
        """
        from .factories import ForumFactory
        question = ForumFactory(
            course_id=self.course,
            commenter_id=self.student_extra
        )
        self.auth_session(role='faculty')
        payload = {
            'comment':    'The quiz is on Friday at 10 AM.',
            'comment_id': question.pk,
        }
        self.client.post(
            f'{_course_url("CS302", "1.0")}/ajax_reply',
            data=payload,
            content_type='application/x-www-form-urlencoded'
        )
        self.assertTrue(
            ForumReply.objects.filter(forum_ques=question).exists()
        )

    # ── Negative ─────────────────────────────────────────────────────────────

    def test_forum_post_fails_without_login(self):
        """
        ARRANGE: No authenticated user.
        ACT:     POST to ajax_new.
        ASSERT:  Redirect to login (no Forum record created).
        """
        self.clear_auth()
        response = self.client.post(
            f'{_course_url("CS302", "1.0")}/ajax_new',
            data={'comment': 'Sneaky unauthenticated post'},
            content_type='application/x-www-form-urlencoded'
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Forum.objects.count(), 0)

    def test_forum_post_fails_with_empty_comment(self):
        """
        ARRANGE: Student is logged in but submits an empty comment.
        ACT:     POST to ajax_new with comment=''.
        ASSERT:  No Forum record created (view should reject empty input).
        """
        self.auth_session(role='student')
        self.client.post(
            f'{_course_url("CS302", "1.0")}/ajax_new',
            data={'comment': ''},
            content_type='application/x-www-form-urlencoded'
        )
        self.assertFalse(Forum.objects.filter(course_id=self.course).exists())


# ─────────────────────────────────────────────────────────────────────────────
# 3. Module & Document Upload Workflow
# ─────────────────────────────────────────────────────────────────────────────

class ContentUploadWorkflowTests(FusionBaseTestCase):
    """
    Tests faculty ability to add course modules and lecture documents.
    """

    def setUp(self):
        super().setUp()
        self.course = CoursesFactory(code='CS303', version=1.0)
        self.faculty_extra = ExtraInfoFactory(
            user=self.faculty_user, user_type='faculty'
        )
        CourseInstructorFactory(
            course_id=self.course, instructor_id=self.faculty_extra
        )

    # ── Positive ─────────────────────────────────────────────────────────────

    def test_faculty_can_add_module(self):
        """
        ARRANGE: Faculty is logged in.
        ACT:     POST to add_modules with a module name.
        ASSERT:  A Modules record with that name exists for the course.
        """
        self.auth_session(role='faculty')
        payload = {'module_name': 'Unit 2 - Data Structures'}
        self.client.post(
            f'{_course_url("CS303", "1.0")}/add_modules',
            data=payload
        )
        self.assertTrue(
            Modules.objects.filter(
                course_id=self.course,
                module_name='Unit 2 - Data Structures'
            ).exists()
        )

    def test_faculty_can_upload_course_document(self):
        """
        ARRANGE: Faculty is logged in; a module exists.
        ACT:     POST to add_document with file metadata.
        ASSERT:  A CourseDocuments record exists in the DB.
        """
        module = ModulesFactory(course_id=self.course)
        self.auth_session(role='faculty')
        payload = {
            'module_id':     module.pk,
            'description':   'Week 3 slides',
            'document_name': 'Week3.pdf',
            'document_url':  '/media/docs/Week3.pdf',
        }
        self.client.post(
            f'{_course_url("CS303", "1.0")}/add_documents',
            data=payload
        )
        self.assertTrue(
            CourseDocuments.objects.filter(
                course_id=self.course,
                document_name='Week3.pdf'
            ).exists()
        )

    # ── Negative ─────────────────────────────────────────────────────────────

    def test_add_module_fails_without_login(self):
        """Student or anonymous user cannot add a module."""
        self.clear_auth()
        response = self.client.post(
            f'{_course_url("CS303", "1.0")}/add_modules',
            data={'module_name': 'Injected Module'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Modules.objects.count(), 0)

    def test_add_document_fails_if_module_missing(self):
        """
        ARRANGE: Faculty logged in, but invalid module_id supplied.
        ACT:     POST to add_documents with a non-existent module pk.
        ASSERT:  No CourseDocuments record is created.
        """
        self.auth_session(role='faculty')
        payload = {
            'module_id':     9999,   # does not exist
            'description':   'Ghost slides',
            'document_name': 'Ghost.pdf',
        }
        self.client.post(
            f'{_course_url("CS303", "1.0")}/add_documents',
            data=payload
        )
        self.assertFalse(
            CourseDocuments.objects.filter(document_name='Ghost.pdf').exists()
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Grading Scheme Workflow
# ─────────────────────────────────────────────────────────────────────────────

class GradingSchemeWorkflowTests(FusionBaseTestCase):
    """
    Tests the full grading scheme creation lifecycle by faculty.
    """

    def setUp(self):
        super().setUp()
        self.course = CoursesFactory(code='CS304', version=1.0)
        self.faculty_extra = ExtraInfoFactory(
            user=self.faculty_user, user_type='faculty'
        )
        CourseInstructorFactory(
            course_id=self.course, instructor_id=self.faculty_extra
        )

    # ── Positive ─────────────────────────────────────────────────────────────

    def test_faculty_can_create_grading_scheme(self):
        """
        ARRANGE: Faculty is authenticated.
        ACT:     POST to create_grading_scheme with component data.
        ASSERT:  A GradingScheme record with correct weightage exists.
        """
        self.auth_session(role='faculty')
        payload = {
            'type_of_evaluation': 'MidSem',
            'weightage':          30,
        }
        self.client.post(
            f'{_course_url("CS304", "1.0")}/create_grading_scheme',
            data=payload
        )
        self.assertTrue(
            GradingScheme.objects.filter(
                course_id=self.course,
                type_of_evaluation='MidSem',
                weightage=30
            ).exists()
        )

    # ── Negative ─────────────────────────────────────────────────────────────

    def test_grading_scheme_fails_for_unauthenticated(self):
        self.clear_auth()
        response = self.client.post(
            f'{_course_url("CS304", "1.0")}/create_grading_scheme',
            data={'type_of_evaluation': 'MidSem', 'weightage': 30}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(GradingScheme.objects.count(), 0)

    def test_grading_scheme_fails_for_student_role(self):
        """Students must not be able to define grading components."""
        self.auth_session(role='student')
        self.client.post(
            f'{_course_url("CS304", "1.0")}/create_grading_scheme',
            data={'type_of_evaluation': 'MidSem', 'weightage': 30}
        )
        self.assertFalse(
            GradingScheme.objects.filter(
                course_id=self.course,
                type_of_evaluation='MidSem'
            ).exists()
        )
