from django.contrib import admin

from .models import (
    Company, JobPost, PlacementApplication, PlacementAnnouncement,
    PlacementResult, PlacementSchedule, PlacementStatistics,
    StudentPlacementProfile,
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display  = ['name', 'sector', 'website', 'created_at']
    search_fields = ['name', 'sector']
    list_filter   = ['sector']


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display  = ['company', 'role', 'job_type', 'ctc', 'deadline', 'is_active']
    list_filter   = ['job_type', 'is_active']
    search_fields = ['company__name', 'role']
    raw_id_fields = ['company', 'created_by']


@admin.register(PlacementSchedule)
class PlacementScheduleAdmin(admin.ModelAdmin):
    list_display  = ['job_post', 'round_number', 'round_name', 'scheduled_at', 'venue']
    list_filter   = ['job_post__company']
    search_fields = ['round_name', 'job_post__company__name']


@admin.register(PlacementApplication)
class PlacementApplicationAdmin(admin.ModelAdmin):
    list_display  = ['student', 'job_post', 'status', 'applied_at', 'updated_at']
    list_filter   = ['status']
    search_fields = ['student__user__username', 'job_post__company__name']
    raw_id_fields = ['student', 'job_post']


@admin.register(PlacementResult)
class PlacementResultAdmin(admin.ModelAdmin):
    list_display  = ['application', 'offer_date', 'ctc_offered', 'is_confirmed']
    list_filter   = ['is_confirmed']
    raw_id_fields = ['application']


@admin.register(StudentPlacementProfile)
class StudentPlacementProfileAdmin(admin.ModelAdmin):
    list_display  = ['student', 'is_placed', 'opted_out', 'updated_at']
    list_filter   = ['is_placed', 'opted_out']
    search_fields = ['student__user__username']
    raw_id_fields = ['student']


@admin.register(PlacementAnnouncement)
class PlacementAnnouncementAdmin(admin.ModelAdmin):
    list_display  = ['title', 'posted_by', 'posted_at', 'is_pinned']
    list_filter   = ['is_pinned']
    search_fields = ['title']


@admin.register(PlacementStatistics)
class PlacementStatisticsAdmin(admin.ModelAdmin):
    list_display  = ['batch_year', 'total_students', 'total_placed', 'total_companies', 'avg_ctc', 'updated_at']
    ordering      = ['-batch_year']
