"""
Placement Cell — unit and integration tests.

Run with: python manage.py test applications.placement_cell.tests
"""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from applications.globals.models import Designation, ExtraInfo, HoldsDesignation
from applications.placement_cell.models import (
    Company, JobPost, PlacementApplication, StudentPlacementProfile,
)
from applications.placement_cell import services, selectors


# ─── helpers ────────────────────────────────────────────────────────────────

def _make_user(username, role='student'):
    user = User.objects.create_user(username=username, password='testpass123')
    extra, _ = ExtraInfo.objects.get_or_create(user=user, defaults={'user_type': role})
    designation, _ = Designation.objects.get_or_create(name=role)
    HoldsDesignation.objects.get_or_create(user=user, designation=designation, working=user)
    return user, extra


def _make_company(name='Acme Corp'):
    return Company.objects.create(name=name, sector='IT')


def _make_job(company, days_until_deadline=7, min_cpi=Decimal('0.0')):
    return JobPost.objects.create(
        company=company,
        role='SDE',
        job_type=JobPost.PLACEMENT,
        min_cpi=min_cpi,
        deadline=timezone.now() + timedelta(days=days_until_deadline),
        is_active=True,
    )


# ─── Service tests ───────────────────────────────────────────────────────────

class ApplyToJobServiceTests(TestCase):

    def setUp(self):
        _, self.extra = _make_user('stu01')
        company       = _make_company()
        self.job      = _make_job(company)

    def test_successful_application(self):
        app = services.apply_to_job(self.extra, self.job.pk)
        self.assertEqual(app.status, PlacementApplication.APPLIED)

    def test_duplicate_application_raises(self):
        services.apply_to_job(self.extra, self.job.pk)
        with self.assertRaises(Exception) as ctx:
            services.apply_to_job(self.extra, self.job.pk)
        self.assertIn('already applied', str(ctx.exception).lower())

    def test_expired_deadline_raises(self):
        job = _make_job(_make_company('OldCo'), days_until_deadline=-1)
        with self.assertRaises(Exception) as ctx:
            services.apply_to_job(self.extra, job.pk)
        self.assertIn('deadline', str(ctx.exception).lower())

    def test_inactive_job_raises(self):
        self.job.is_active = False
        self.job.save()
        with self.assertRaises(Exception) as ctx:
            services.apply_to_job(self.extra, self.job.pk)
        self.assertIn('active', str(ctx.exception).lower())

    @patch('applications.placement_cell.selectors.get_student_published_cpi')
    def test_low_cpi_raises(self, mock_cpi):
        mock_cpi.return_value = Decimal('6.0')
        job = _make_job(_make_company('HighBarCo'), min_cpi=Decimal('7.5'))
        with self.assertRaises(Exception) as ctx:
            services.apply_to_job(self.extra, job.pk)
        self.assertIn('cpi', str(ctx.exception).lower())

    @patch('applications.placement_cell.selectors.get_student_published_cpi')
    def test_sufficient_cpi_succeeds(self, mock_cpi):
        mock_cpi.return_value = Decimal('8.5')
        job = _make_job(_make_company('GoodCo'), min_cpi=Decimal('7.5'))
        app = services.apply_to_job(self.extra, job.pk)
        self.assertIsNotNone(app.pk)

    def test_placed_student_cannot_apply(self):
        StudentPlacementProfile.objects.create(student=self.extra, is_placed=True)
        with self.assertRaises(Exception) as ctx:
            services.apply_to_job(self.extra, self.job.pk)
        self.assertIn('placed', str(ctx.exception).lower())


class BulkStatusUpdateTests(TestCase):

    def setUp(self):
        _, extra1 = _make_user('stu02')
        _, extra2 = _make_user('stu03')
        company   = _make_company('BulkCo')
        job       = _make_job(company)
        self.app1 = PlacementApplication.objects.create(job_post=job, student=extra1)
        self.app2 = PlacementApplication.objects.create(job_post=job, student=extra2)

    def test_bulk_shortlist(self):
        count = services.bulk_update_application_status(
            [self.app1.pk, self.app2.pk], PlacementApplication.SHORTLISTED
        )
        self.assertEqual(count, 2)
        self.app1.refresh_from_db()
        self.assertEqual(self.app1.status, PlacementApplication.SHORTLISTED)

    def test_invalid_status_raises(self):
        with self.assertRaises(Exception):
            services.bulk_update_application_status([self.app1.pk], 'invalid_status')


# ─── Selector tests ──────────────────────────────────────────────────────────

class SelectorTests(TestCase):

    def test_list_active_jobs_excludes_expired(self):
        company = _make_company('ExpiredCo')
        _make_job(company, days_until_deadline=-1)
        jobs = list(selectors.list_active_job_posts())
        self.assertEqual(len(jobs), 0)

    def test_list_active_jobs_includes_future(self):
        company = _make_company('FutureCo')
        _make_job(company, days_until_deadline=5)
        jobs = list(selectors.list_active_job_posts())
        self.assertEqual(len(jobs), 1)

    @patch('applications.placement_cell.selectors.get_student_published_cpi')
    def test_get_student_published_cpi_none_when_no_results(self, mock_inner):
        mock_inner.return_value = None
        result = selectors.get_student_published_cpi(None)
        self.assertIsNone(result)

    def test_get_student_profile_creates_if_missing(self):
        _, extra = _make_user('stu04')
        self.assertFalse(StudentPlacementProfile.objects.filter(student=extra).exists())
        profile = selectors.get_student_profile(extra)
        self.assertIsNotNone(profile.pk)


# ─── API permission tests ────────────────────────────────────────────────────

class APIPermissionTests(TestCase):

    def setUp(self):
        self.client              = APIClient()
        self.student_user, _     = _make_user('api_stu', 'student')
        self.officer_user, _     = _make_user('api_ofc', 'placement_officer')

    def _auth(self, user):
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_student_cannot_access_officer_jobs(self):
        self._auth(self.student_user)
        resp = self.client.get('/placement-cell/api/officer/jobs/')
        self.assertEqual(resp.status_code, 403)

    def test_officer_can_access_officer_jobs(self):
        self._auth(self.officer_user)
        resp = self.client.get('/placement-cell/api/officer/jobs/')
        self.assertEqual(resp.status_code, 200)

    def test_student_can_access_student_jobs(self):
        self._auth(self.student_user)
        resp = self.client.get('/placement-cell/api/stu/jobs/')
        self.assertEqual(resp.status_code, 200)

    def test_unauthenticated_rejected(self):
        self.client.credentials()
        resp = self.client.get('/placement-cell/api/stu/jobs/')
        self.assertIn(resp.status_code, [401, 403])
