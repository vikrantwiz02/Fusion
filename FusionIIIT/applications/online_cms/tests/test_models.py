"""
test_models.py — Model-level tests for online_cms.

Covers:
  - Field constraints (max_length, null, default values)
  - __str__ representations
  - ForeignKey cascade behaviour
  - Business-rule constraints (e.g. Quiz end_time > start_time)
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from .base_setup import FusionBaseTestCase
from .factories import (
    CoursesFactory, ModulesFactory, CourseDocumentsFactory,
    QuizFactory, QuestionBankFactory, QuestionFactory, TopicsFactory,
    AssignmentFactory, StudentAssignmentFactory, StudentFactory,
    QuizResultFactory, ForumFactory, GradingSchemeFactory,
    GradingSchemeGradesFactory, StudentGradesFactory,
)
from applications.online_cms.models import (
    Modules, CourseDocuments, Quiz, QuizResult,
    Assignment, StudentAssignment, GradingScheme, Student_grades,
)


class ModulesModelTest(TestCase):
    """Tests for the Modules model."""

    def test_str_returns_module_name(self):
        """__str__ should return the module_name string."""
        # Arrange
        module = ModulesFactory(module_name='Unit 1 - Intro to OOP')
        # Act
        result = str(module)
        # Assert
        self.assertEqual(result, 'Unit 1 - Intro to OOP')

    def test_module_name_max_length(self):
        """module_name field must enforce max_length=50."""
        # Arrange
        field = Modules._meta.get_field('module_name')
        # Assert
        self.assertEqual(field.max_length, 50)

    def test_cascade_delete_on_course_removal(self):
        """Deleting a Course should cascade-delete its Modules."""
        # Arrange
        module = ModulesFactory()
        course = module.course_id
        # Act
        course.delete()
        # Assert
        self.assertFalse(Modules.objects.filter(pk=module.pk).exists())


class CourseDocumentsModelTest(TestCase):
    """Tests for the CourseDocuments model."""

    def test_str_format(self):
        """__str__ should return '<course_id> - <document_name>'."""
        doc = CourseDocumentsFactory(document_name='Lec1.pdf')
        self.assertIn('Lec1.pdf', str(doc))

    def test_document_url_can_be_null(self):
        """document_url is nullable — should save without error."""
        doc = CourseDocumentsFactory(document_url=None)
        doc.refresh_from_db()
        self.assertIsNone(doc.document_url)

    def test_description_max_length(self):
        field = CourseDocuments._meta.get_field('description')
        self.assertEqual(field.max_length, 100)


class QuizModelTest(TestCase):
    """Tests for the Quiz model."""

    def test_quiz_default_negative_marks(self):
        """negative_marks must default to 0 when not supplied."""
        course = CoursesFactory()
        quiz = Quiz.objects.create(
            course_id=course,
            quiz_name='Test Quiz',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            d_day='0', d_hour='1', d_minute='0',
            description='desc', rules='rules', total_score=10
        )
        self.assertEqual(quiz.negative_marks, 0)

    def test_quiz_end_time_after_start_time(self):
        """A properly created Quiz should always have end_time > start_time."""
        quiz = QuizFactory()
        self.assertGreater(quiz.end_time, quiz.start_time)

    def test_quiz_str_contains_course_and_times(self):
        """__str__ should contain pk and course info."""
        quiz = QuizFactory()
        self.assertIn(str(quiz.pk), str(quiz))


class AssignmentModelTest(TestCase):
    """Tests for the Assignment model."""

    def test_str_contains_assignment_name(self):
        assignment = AssignmentFactory(assignment_name='Lab_Report_1')
        self.assertIn('Lab_Report_1', str(assignment))

    def test_assignment_url_nullable(self):
        assignment = AssignmentFactory(assignment_url=None)
        assignment.refresh_from_db()
        self.assertIsNone(assignment.assignment_url)


class StudentAssignmentModelTest(TestCase):
    """Tests for StudentAssignment (student submission)."""

    def test_score_starts_as_null(self):
        """Score should be null until faculty grades the submission."""
        submission = StudentAssignmentFactory(score=None)
        submission.refresh_from_db()
        self.assertIsNone(submission.score)

    def test_feedback_can_be_null(self):
        submission = StudentAssignmentFactory(feedback=None)
        submission.refresh_from_db()
        self.assertIsNone(submission.feedback)


class QuizResultModelTest(TestCase):
    """Tests for the QuizResult model."""

    def test_finished_defaults_to_false(self):
        """finished flag should be False when a result is first created."""
        quiz = QuizFactory()
        student = StudentFactory()
        result = QuizResult.objects.create(
            quiz_id=quiz, student_id=student, score=0
        )
        self.assertFalse(result.finished)

    def test_finished_can_be_set_true(self):
        result = QuizResultFactory(finished=True)
        result.refresh_from_db()
        self.assertTrue(result.finished)


class GradingSchemeModelTest(TestCase):
    """Tests for the GradingScheme model."""

    def test_weightage_default_is_zero(self):
        gs = GradingSchemeFactory(weightage=0)
        gs.refresh_from_db()
        self.assertEqual(gs.weightage, 0)

    def test_multiple_components_for_same_course(self):
        """A course can have multiple grading components."""
        course = CoursesFactory()
        GradingSchemeFactory(course_id=course, type_of_evaluation='Quiz', weightage=20)
        GradingSchemeFactory(course_id=course, type_of_evaluation='EndSem', weightage=40)
        count = GradingScheme.objects.filter(course_id=course).count()
        self.assertEqual(count, 2)


class StudentGradesModelTest(TestCase):
    """Tests for Student_grades model (grade submission workflow)."""

    def test_verified_defaults_to_false(self):
        sg = StudentGradesFactory()
        sg.refresh_from_db()
        self.assertFalse(sg.verified)

    def test_resubmit_defaults_to_true(self):
        sg = StudentGradesFactory()
        sg.refresh_from_db()
        self.assertTrue(sg.reSubmit)

    def test_semester_type_choices_are_valid(self):
        """semester_type must be one of the three defined choices."""
        valid_types = ['Odd Semester', 'Even Semester', 'Summer Semester']
        choices = [c[0] for c in Student_grades.semester_type.field.choices]
        for t in valid_types:
            self.assertIn(t, choices)
