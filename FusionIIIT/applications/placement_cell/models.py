from django.db import models
from django.contrib.auth.models import User

from applications.globals.models import ExtraInfo


class Company(models.Model):
    name        = models.CharField(max_length=255, unique=True)
    sector      = models.CharField(max_length=100)
    website     = models.URLField(blank=True)
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Companies'

    def __str__(self):
        return self.name


class JobPost(models.Model):
    PLACEMENT  = 'placement'
    INTERNSHIP = 'internship'
    PPO        = 'ppo'
    TYPE_CHOICES = [(PLACEMENT, 'Placement'), (INTERNSHIP, 'Internship'), (PPO, 'Pre Placement Offer')]

    company              = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='job_posts')
    role                 = models.CharField(max_length=200)
    job_type             = models.CharField(max_length=20, choices=TYPE_CHOICES, default=PLACEMENT)
    description          = models.TextField(blank=True)
    ctc                  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stipend              = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location             = models.CharField(max_length=200, blank=True)
    eligible_batches     = models.JSONField(default=list)
    eligible_programmes  = models.JSONField(default=list)
    eligible_disciplines = models.JSONField(default=list)
    min_cpi              = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    apply_link           = models.URLField(blank=True)
    deadline             = models.DateTimeField()
    is_active            = models.BooleanField(default=True)
    created_by           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_job_posts')
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company.name} — {self.role}"


class PlacementSchedule(models.Model):
    job_post     = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='schedules')
    round_name   = models.CharField(max_length=100)
    round_number = models.PositiveSmallIntegerField()
    scheduled_at = models.DateTimeField()
    venue        = models.CharField(max_length=200, blank=True)
    notes        = models.TextField(blank=True)

    class Meta:
        ordering = ['round_number']

    def __str__(self):
        return f"{self.job_post} — Round {self.round_number}: {self.round_name}"


class PlacementApplication(models.Model):
    APPLIED     = 'applied'
    SHORTLISTED = 'shortlisted'
    REJECTED    = 'rejected'
    PLACED      = 'placed'
    WITHDRAWN   = 'withdrawn'
    STATUS_CHOICES = [
        (APPLIED,     'Applied'),
        (SHORTLISTED, 'Shortlisted'),
        (REJECTED,    'Rejected'),
        (PLACED,      'Placed'),
        (WITHDRAWN,   'Withdrawn'),
    ]

    job_post   = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='applications')
    student    = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE, related_name='placement_applications')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default=APPLIED)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('job_post', 'student')
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.student} → {self.job_post} [{self.status}]"


class PlacementResult(models.Model):
    application  = models.OneToOneField(PlacementApplication, on_delete=models.CASCADE, related_name='result')
    offer_date   = models.DateField()
    joining_date = models.DateField(null=True, blank=True)
    ctc_offered  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    offer_letter = models.FileField(upload_to='placement/offer_letters/', blank=True)
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"Result: {self.application}"


class StudentPlacementProfile(models.Model):
    student    = models.OneToOneField(ExtraInfo, on_delete=models.CASCADE, related_name='placement_profile')
    resume_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    is_placed  = models.BooleanField(default=False)
    opted_out  = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.student}"


class PlacementAnnouncement(models.Model):
    title     = models.CharField(max_length=300)
    body      = models.TextField()
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    posted_at = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_pinned', '-posted_at']

    def __str__(self):
        return self.title


class OffCampusPlacement(models.Model):
    PLACEMENT  = 'placement'
    INTERNSHIP = 'internship'
    TYPE_CHOICES = [(PLACEMENT, 'Placement'), (INTERNSHIP, 'Internship')]

    student      = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE, related_name='offcampus_placements')
    company_name = models.CharField(max_length=255)
    role         = models.CharField(max_length=200)
    offer_type   = models.CharField(max_length=20, choices=TYPE_CHOICES, default=PLACEMENT)
    ctc          = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stipend      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    offer_date   = models.DateField()
    notes        = models.TextField(blank=True)
    added_by     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='added_offcampus_placements')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-offer_date']

    def __str__(self):
        return f"{self.student} — {self.company_name} ({self.offer_type})"


class PlacementStatistics(models.Model):
    batch_year      = models.CharField(max_length=10, unique=True)
    total_students  = models.PositiveIntegerField(default=0)
    total_placed    = models.PositiveIntegerField(default=0)
    total_companies = models.PositiveIntegerField(default=0)
    avg_ctc         = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    highest_ctc     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Placement Statistics'
        ordering = ['-batch_year']

    def __str__(self):
        return f"Stats {self.batch_year}: {self.total_placed}/{self.total_students} placed"
