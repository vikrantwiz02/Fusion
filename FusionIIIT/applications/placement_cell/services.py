"""
Write-only business logic layer.
All DB writes happen here. Views call these functions after validation.
"""
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    Company, JobPost, OffCampusPlacement, PlacementApplication, PlacementAnnouncement,
    PlacementResult, PlacementStatistics, StudentPlacementProfile,
)
from .selectors import get_student_published_cpi, get_student_profile


# ---------- Company ----------

def create_company(data: dict) -> Company:
    return Company.objects.create(**data)


def update_company(company_id: int, data: dict) -> Company:
    Company.objects.filter(pk=company_id).update(**data)
    return Company.objects.get(pk=company_id)


def delete_company(company_id: int) -> None:
    Company.objects.filter(pk=company_id).delete()


# ---------- Job Post ----------

def create_job_post(data: dict, created_by_user) -> JobPost:
    data = dict(data)
    data['created_by'] = created_by_user
    return JobPost.objects.create(**data)


def update_job_post(job_post_id: int, data: dict) -> JobPost:
    JobPost.objects.filter(pk=job_post_id).update(**data)
    return JobPost.objects.select_related('company').get(pk=job_post_id)


def toggle_job_post_active(job_post_id: int) -> JobPost:
    job = JobPost.objects.get(pk=job_post_id)
    job.is_active = not job.is_active
    job.save(update_fields=['is_active'])
    return job


# ---------- Application ----------

def apply_to_job(student_extra_info, job_post_id: int) -> PlacementApplication:
    job = JobPost.objects.select_related('company').get(pk=job_post_id)

    if not job.is_active:
        raise ValidationError("This job post is no longer active.")
    if timezone.now() > job.deadline:
        raise ValidationError("The application deadline has passed.")

    if PlacementApplication.objects.filter(job_post=job, student=student_extra_info).exists():
        raise ValidationError("You have already applied to this job post.")

    profile = get_student_profile(student_extra_info)
    if profile.is_placed:
        raise ValidationError("You are already placed and cannot apply to more openings.")

    if job.min_cpi > 0:
        cpi = get_student_published_cpi(student_extra_info)
        if cpi is None or cpi < job.min_cpi:
            raise ValidationError(
                f"Your published CPI does not meet the minimum requirement of {job.min_cpi}."
            )

    return PlacementApplication.objects.create(job_post=job, student=student_extra_info)


def withdraw_application(application_id: int, student_extra_info) -> None:
    app = PlacementApplication.objects.get(pk=application_id, student=student_extra_info)
    if app.status == PlacementApplication.PLACED:
        raise ValidationError("Cannot withdraw a confirmed placement offer.")
    app.status = PlacementApplication.WITHDRAWN
    app.save(update_fields=['status', 'updated_at'])


def update_application_status(application_id: int, new_status: str) -> PlacementApplication:
    valid = {s for s, _ in PlacementApplication.STATUS_CHOICES}
    if new_status not in valid:
        raise ValidationError(f"Invalid status '{new_status}'.")
    app = PlacementApplication.objects.select_related('student', 'job_post').get(pk=application_id)
    app.status = new_status
    app.save(update_fields=['status', 'updated_at'])

    if new_status == PlacementApplication.PLACED:
        profile, _ = StudentPlacementProfile.objects.get_or_create(student=app.student)
        if not profile.is_placed:
            profile.is_placed = True
            profile.save(update_fields=['is_placed'])

    return app


def bulk_update_application_status(application_ids: list, new_status: str) -> int:
    valid = {s for s, _ in PlacementApplication.STATUS_CHOICES}
    if new_status not in valid:
        raise ValidationError(f"Invalid status '{new_status}'.")

    with transaction.atomic():
        updated = PlacementApplication.objects.filter(pk__in=application_ids).update(
            status=new_status,
            updated_at=timezone.now(),
        )
        if new_status == PlacementApplication.PLACED:
            student_ids = list(
                PlacementApplication.objects.filter(pk__in=application_ids).values_list('student_id', flat=True)
            )
            StudentPlacementProfile.objects.filter(student_id__in=student_ids).update(is_placed=True)

    return updated


# ---------- Student Profile ----------

def upsert_student_profile(student_extra_info, data: dict) -> StudentPlacementProfile:
    allowed = {'resume_url', 'linkedin_url', 'github_url', 'opted_out'}
    clean   = {k: v for k, v in data.items() if k in allowed}
    profile, _ = StudentPlacementProfile.objects.get_or_create(student=student_extra_info)
    # opted_out is one-way: once True it cannot be reverted via API
    if profile.opted_out:
        clean.pop('opted_out', None)
    for k, v in clean.items():
        setattr(profile, k, v)
    profile.save()
    return profile


# ---------- Off-Campus Placements ----------

def add_offcampus_placement(data: dict, added_by_user) -> OffCampusPlacement:
    data = dict(data)
    data['added_by'] = added_by_user
    ocp = OffCampusPlacement.objects.create(**data)
    profile, _ = StudentPlacementProfile.objects.get_or_create(student=ocp.student)
    if not profile.is_placed:
        profile.is_placed = True
        profile.save(update_fields=['is_placed'])
    return ocp


def delete_offcampus_placement(placement_id: int) -> None:
    OffCampusPlacement.objects.filter(pk=placement_id).delete()


# ---------- Announcements ----------

def create_announcement(data: dict, posted_by_user) -> PlacementAnnouncement:
    return PlacementAnnouncement.objects.create(posted_by=posted_by_user, **data)


def delete_announcement(announcement_id: int) -> None:
    PlacementAnnouncement.objects.filter(pk=announcement_id).delete()


# ---------- Statistics ----------

def refresh_statistics(batch_year: str) -> PlacementStatistics:
    from applications.academic_information.models import Student

    students = Student.objects.filter(batch_id__year=batch_year)
    total    = students.count()

    placed_apps = PlacementApplication.objects.filter(
        student__user__username__in=students.values_list('id__user__username', flat=True),
        status=PlacementApplication.PLACED,
    ).select_related('result')

    placed   = placed_apps.count()
    companies = (
        placed_apps.values('job_post__company').distinct().count()
    )

    ctc_values = [
        app.result.ctc_offered
        for app in placed_apps
        if hasattr(app, 'result') and app.result.ctc_offered is not None
    ]
    avg_ctc     = sum(ctc_values) / len(ctc_values) if ctc_values else None
    highest_ctc = max(ctc_values) if ctc_values else None

    stats, _ = PlacementStatistics.objects.update_or_create(
        batch_year=batch_year,
        defaults={
            'total_students':  total,
            'total_placed':    placed,
            'total_companies': companies,
            'avg_ctc':         avg_ctc,
            'highest_ctc':     highest_ctc,
        },
    )
    return stats
