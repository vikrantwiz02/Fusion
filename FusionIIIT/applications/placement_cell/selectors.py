"""
Read-only query layer. No writes happen here.
All CPI data is fetched live from the examination module.
"""
from decimal import Decimal
from django.utils import timezone

from .models import (
    Company, JobPost, PlacementApplication, PlacementAnnouncement,
    PlacementStatistics, StudentPlacementProfile,
)


def get_student_profile(student_extra_info) -> StudentPlacementProfile:
    profile, _ = StudentPlacementProfile.objects.get_or_create(student=student_extra_info)
    return profile


def get_student_published_cpi(student_extra_info):
    """
    Returns the student's CPI calculated from the latest published semester result,
    or None if no results have been published yet.

    Reuses calculation logic from the examination module to avoid duplication.
    """
    try:
        from applications.examination.models import ResultAnnouncement
        from applications.examination.api.views import calculate_cpi_for_student
        from applications.academic_information.models import Student

        student_obj = Student.objects.select_related('id').get(id=student_extra_info)

        latest = (
            ResultAnnouncement.objects
            .filter(batch=student_obj.batch_id, announced=True)
            .order_by('-semester')
            .first()
        )
        if not latest:
            return None

        cpi_value, _, _ = calculate_cpi_for_student(student_obj, latest.semester, latest.semester_type)
        return cpi_value
    except Exception:
        return None


def list_active_job_posts(student_extra_info=None):
    """
    Returns active, non-expired job posts.
    If student_extra_info is given, filters by eligibility (batch/programme/discipline).
    """
    now = timezone.now()
    qs = JobPost.objects.filter(is_active=True, deadline__gte=now).select_related('company')

    if student_extra_info is None:
        return qs

    try:
        from applications.academic_information.models import Student
        student = Student.objects.select_related('batch_id__discipline_id', 'programme').get(id=student_extra_info)
        batch_year = str(student.batch_id.year) if student.batch_id else None
        programme  = student.programme if student.programme else None
        discipline = student.batch_id.discipline_id.acronym if student.batch_id and student.batch_id.discipline_id else None

        eligible = []
        for job in qs:
            batch_ok      = not job.eligible_batches or (batch_year and batch_year in job.eligible_batches)
            programme_ok  = not job.eligible_programmes or (programme and programme in job.eligible_programmes)
            discipline_ok = not job.eligible_disciplines or (discipline and discipline in job.eligible_disciplines)
            if batch_ok and programme_ok and discipline_ok:
                eligible.append(job.pk)
        return qs.filter(pk__in=eligible)
    except Exception:
        return qs


def list_job_posts_admin():
    return JobPost.objects.select_related('company').prefetch_related('schedules').all()


def get_job_post_detail(job_post_id: int) -> JobPost:
    return JobPost.objects.select_related('company').prefetch_related('schedules').get(pk=job_post_id)


def list_applications_for_student(student_extra_info):
    return (
        PlacementApplication.objects
        .filter(student=student_extra_info)
        .select_related('job_post__company')
        .prefetch_related('job_post__schedules')
    )


def list_applications_for_job_post(job_post_id: int):
    return (
        PlacementApplication.objects
        .filter(job_post_id=job_post_id)
        .select_related('student__user', 'job_post__company')
    )


def list_all_applications_admin(filters: dict = None):
    qs = PlacementApplication.objects.select_related('student__user', 'job_post__company')
    if filters:
        if filters.get('job_post_id'):
            qs = qs.filter(job_post_id=filters['job_post_id'])
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])
    return qs


def list_announcements():
    return PlacementAnnouncement.objects.all()


def list_companies():
    return Company.objects.all()


def get_placement_statistics(batch_year: str = None):
    if batch_year:
        try:
            return PlacementStatistics.objects.get(batch_year=batch_year)
        except PlacementStatistics.DoesNotExist:
            return None
    return PlacementStatistics.objects.all()


def export_placement_data_rows(filters: dict = None) -> list:
    """Returns serializable row dicts for Excel export."""
    qs = list_all_applications_admin(filters)
    rows = []
    for app in qs:
        u = app.student.user
        rows.append({
            'roll_no':    u.username,
            'name':       f"{u.first_name} {u.last_name}".strip(),
            'email':      u.email,
            'company':    app.job_post.company.name,
            'role':       app.job_post.role,
            'job_type':   app.job_post.job_type,
            'status':     app.status,
            'applied_at': app.applied_at.strftime('%Y-%m-%d') if app.applied_at else '',
        })
    return rows
