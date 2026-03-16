"""
factories.py — factory_boy definitions for online_cms dummy data generation.

Generates realistic Indian university data using Faker.
All ForeignKey / M2M relationships are handled via SubFactory.

Usage example:
    course = CourseFactory()
    quiz   = QuizFactory(course_id=course)
    qb     = QuestionBankFactory(course_id=course)
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# ── Import online_cms models ──────────────────────────────────────────────────
from applications.online_cms.models import (
    Modules,
    CourseDocuments,
    AttendanceFiles,
    CourseVideo,
    Topics,
    QuestionBank,
    Question,
    Quiz,
    QuizQuestion,
    Practice,
    PracticeQuestion,
    StudentAnswer,
    Assignment,
    StudentAssignment,
    QuizResult,
    Forum,
    ForumReply,
    GradingScheme,
    GradingScheme_grades,
    Student_grades,
    StudentEvaluation,
)

# ── External model factories (minimal stubs) ──────────────────────────────────
# These wrap models from other apps so online_cms factories stay self-contained.

class UserFactory(DjangoModelFactory):
    """Creates a plain Django auth user with a realistic Indian roll number."""
    class Meta:
        model = User

    # e.g. "23BCS265", "22ECE101"
    username  = factory.Sequence(lambda n: f'23BCS{200 + n}')
    password  = factory.PostGenerationMethodCall('set_password', 'testpassword123')
    email     = factory.LazyAttribute(lambda o: f'{o.username}@iiitdmj.ac.in')
    first_name = factory.Faker('first_name', locale='en_IN')
    last_name  = factory.Faker('last_name',  locale='en_IN')


class ExtraInfoFactory(DjangoModelFactory):
    """Stub factory for globals.ExtraInfo (used by QuestionBank & Forum)."""
    class Meta:
        model = 'globals.ExtraInfo'   # lazy string — avoids hard import

    user      = factory.SubFactory(UserFactory)
    user_type = 'faculty'   # default; override with ExtraInfoFactory(user_type='student')


class CoursesFactory(DjangoModelFactory):
    """
    Stub factory for programme_curriculum.Course.
    Generates codes like CS101, CS102 …
    """
    class Meta:
        model = 'programme_curriculum.Course'

    code    = factory.Sequence(lambda n: f'CS{100 + n}')
    name    = factory.Faker('catch_phrase')
    credits = 4


class StudentFactory(DjangoModelFactory):
    """Stub factory for academic_information.Student."""
    class Meta:
        model = 'academic_information.Student'

    id = factory.SubFactory(ExtraInfoFactory, user_type='student')


class CourseInstructorFactory(DjangoModelFactory):
    """Stub factory for programme_curriculum.CourseInstructor."""
    class Meta:
        model = 'programme_curriculum.CourseInstructor'

    course_id     = factory.SubFactory(CoursesFactory)
    instructor_id = factory.SubFactory(ExtraInfoFactory, user_type='faculty')


# ── online_cms model factories ────────────────────────────────────────────────

class ModulesFactory(DjangoModelFactory):
    """Creates a course module (e.g. 'Unit 1 – Introduction to OOP')."""
    class Meta:
        model = Modules

    module_name = factory.Sequence(lambda n: f'Module {n + 1}')
    course_id   = factory.SubFactory(CoursesFactory)


class CourseDocumentsFactory(DjangoModelFactory):
    """Creates a lecture slide / PDF document uploaded by faculty."""
    class Meta:
        model = CourseDocuments

    course_id     = factory.SubFactory(CoursesFactory)
    module_id     = factory.SubFactory(ModulesFactory)
    description   = factory.Faker('sentence', nb_words=6)
    document_name = factory.Sequence(lambda n: f'Lecture_{n + 1}.pdf')
    document_url  = factory.LazyAttribute(
        lambda o: f'/media/documents/{o.document_name}'
    )


class AttendanceFilesFactory(DjangoModelFactory):
    """Creates an attendance Excel file uploaded by faculty."""
    class Meta:
        model = AttendanceFiles

    course_id = factory.SubFactory(CoursesFactory)
    file_name = factory.Sequence(lambda n: f'Attendance_Week{n + 1}.xlsx')
    file_url  = factory.LazyAttribute(
        lambda o: f'/media/attendance/{o.file_name}'
    )


class CourseVideoFactory(DjangoModelFactory):
    """Creates a lecture video record."""
    class Meta:
        model = CourseVideo

    course_id   = factory.SubFactory(CoursesFactory)
    description = factory.Faker('sentence', nb_words=8)
    video_name  = factory.Sequence(lambda n: f'Lecture_{n + 1}.mp4')
    video_url   = factory.LazyAttribute(
        lambda o: f'/media/videos/{o.video_name}'
    )


class TopicsFactory(DjangoModelFactory):
    """Creates a question-bank topic."""
    class Meta:
        model = Topics

    course_id  = factory.SubFactory(CoursesFactory)
    topic_name = factory.Faker('catch_phrase')


class QuestionBankFactory(DjangoModelFactory):
    """Creates a question bank owned by a faculty member."""
    class Meta:
        model = QuestionBank

    instructor_id = factory.SubFactory(ExtraInfoFactory, user_type='faculty')
    course_id     = factory.SubFactory(CoursesFactory)
    name          = factory.Sequence(lambda n: f'QB_{n + 1}_MidSem')


class QuestionFactory(DjangoModelFactory):
    """Creates a 4-option MCQ with answer stored as integer index (1–4)."""
    class Meta:
        model = Question

    question_bank = factory.SubFactory(QuestionBankFactory)
    topic         = factory.SubFactory(TopicsFactory)
    question      = factory.Faker('sentence', nb_words=12)
    options1      = factory.Faker('word')
    options2      = factory.Faker('word')
    options3      = factory.Faker('word')
    options4      = factory.Faker('word')
    options5      = None   # optional 5th option
    answer        = 1      # correct option index
    image         = None
    marks         = factory.Iterator([1, 2, 4])


class QuizFactory(DjangoModelFactory):
    """Creates a quiz that is open for 2 hours from now."""
    class Meta:
        model = Quiz

    course_id        = factory.SubFactory(CoursesFactory)
    quiz_name        = factory.Sequence(lambda n: f'Quiz_{n + 1}')
    start_time       = factory.LazyFunction(timezone.now)
    end_time         = factory.LazyFunction(
        lambda: timezone.now() + timedelta(hours=2)
    )
    d_day            = '0'
    d_hour           = '2'
    d_minute         = '0'
    negative_marks   = 0.25
    number_of_question = 10
    description      = factory.Faker('paragraph', nb_sentences=2)
    rules            = factory.Faker('paragraph', nb_sentences=3)
    total_score      = 20


class QuizQuestionFactory(DjangoModelFactory):
    """Links a Question to a Quiz."""
    class Meta:
        model = QuizQuestion

    quiz_id  = factory.SubFactory(QuizFactory)
    question = factory.SubFactory(QuestionFactory)


class AssignmentFactory(DjangoModelFactory):
    """Creates an assignment with a 7-day submission window."""
    class Meta:
        model = Assignment

    course_id       = factory.SubFactory(CoursesFactory)
    submit_date     = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=7)
    )
    assignment_name = factory.Sequence(lambda n: f'Assignment_{n + 1}')
    assignment_url  = factory.LazyAttribute(
        lambda o: f'/media/assignments/{o.assignment_name}.pdf'
    )


class StudentAssignmentFactory(DjangoModelFactory):
    """Creates a student submission for an assignment."""
    class Meta:
        model = StudentAssignment

    student_id    = factory.SubFactory(StudentFactory)
    assignment_id = factory.SubFactory(AssignmentFactory)
    upload_url    = factory.Faker('url')
    score         = None      # not yet graded
    feedback      = None
    assign_name   = factory.LazyAttribute(
        lambda o: o.assignment_id.assignment_name
    )


class QuizResultFactory(DjangoModelFactory):
    """Creates a quiz result record for a student."""
    class Meta:
        model = QuizResult

    quiz_id    = factory.SubFactory(QuizFactory)
    student_id = factory.SubFactory(StudentFactory)
    score      = 14
    finished   = True


class ForumFactory(DjangoModelFactory):
    """Creates a forum post (question or announcement)."""
    class Meta:
        model = Forum

    course_id    = factory.SubFactory(CoursesFactory)
    commenter_id = factory.SubFactory(ExtraInfoFactory)
    comment      = factory.Faker('paragraph', nb_sentences=2)


class ForumReplyFactory(DjangoModelFactory):
    """Creates a reply to a forum post."""
    class Meta:
        model = ForumReply

    forum_ques  = factory.SubFactory(ForumFactory)
    forum_reply = factory.SubFactory(ForumFactory)


class GradingSchemeFactory(DjangoModelFactory):
    """Creates one grading component (e.g. Quiz = 20%)."""
    class Meta:
        model = GradingScheme

    course_id          = factory.SubFactory(CoursesFactory)
    type_of_evaluation = factory.Iterator(
        ['Quiz', 'Assignment', 'MidSem', 'EndSem', 'Project']
    )
    weightage = factory.Iterator([20, 20, 20, 30, 10])


class GradingSchemeGradesFactory(DjangoModelFactory):
    """Creates a standard 10-grade band (O to F) for a course."""
    class Meta:
        model = GradingScheme_grades

    course_id      = factory.SubFactory(CoursesFactory)
    O_Lower        = 90; O_Upper       = 100
    A_plus_Lower   = 80; A_plus_Upper  = 90
    A_Lower        = 70; A_Upper       = 80
    B_plus_Lower   = 65; B_plus_Upper  = 70
    B_Lower        = 60; B_Upper       = 65
    C_plus_Lower   = 55; C_plus_Upper  = 60
    C_Lower        = 50; C_Upper       = 55
    D_plus_Lower   = 45; D_plus_Upper  = 50
    D_Lower        = 40; D_Upper       = 45
    F_Lower        = 0;  F_Upper       = 40


class StudentGradesFactory(DjangoModelFactory):
    """Creates a submitted grade sheet for one student."""
    class Meta:
        model = Student_grades

    course_id     = factory.SubFactory(CoursesFactory)
    semester      = 3
    year          = 2024
    roll_no       = factory.Sequence(lambda n: f'23BCS{200 + n}')
    grade         = factory.Iterator(['O', 'A+', 'A', 'B+', 'B', 'C', 'F'])
    batch         = 2023
    remarks       = None
    verified      = False
    reSubmit      = True
    academic_year = '2024-2025'
    semester_type = 'Odd Semester'


class StudentEvaluationFactory(DjangoModelFactory):
    """Records a student's marks for one grading component."""
    class Meta:
        model = StudentEvaluation

    student_id    = factory.SubFactory(StudentFactory)
    evaluation_id = factory.SubFactory(GradingSchemeFactory)
    marks         = 16
    total_marks   = 20
