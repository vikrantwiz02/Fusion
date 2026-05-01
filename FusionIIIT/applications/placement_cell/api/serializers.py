from rest_framework import serializers

from applications.placement_cell.models import (
    Company, JobPost, PlacementSchedule, PlacementApplication,
    PlacementResult, StudentPlacementProfile, PlacementAnnouncement,
    PlacementStatistics, OffCampusPlacement,
)


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Company
        fields = ['id', 'name', 'sector', 'website', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class PlacementScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PlacementSchedule
        fields = ['id', 'round_number', 'round_name', 'scheduled_at', 'venue', 'notes']
        read_only_fields = ['id']


class JobPostListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_id   = serializers.IntegerField(source='company.id', read_only=True)
    days_left    = serializers.SerializerMethodField()

    class Meta:
        model  = JobPost
        fields = [
            'id', 'company_id', 'company_name', 'role', 'job_type', 'ctc', 'stipend',
            'location', 'min_cpi', 'deadline', 'is_active', 'days_left', 'apply_link',
            'eligible_batches', 'eligible_programmes', 'eligible_disciplines',
        ]

    def get_days_left(self, obj):
        from django.utils import timezone
        delta = obj.deadline - timezone.now()
        return max(0, delta.days)


class JobPostDetailSerializer(serializers.ModelSerializer):
    company   = CompanySerializer(read_only=True)
    schedules = PlacementScheduleSerializer(many=True, read_only=True)
    days_left = serializers.SerializerMethodField()

    class Meta:
        model  = JobPost
        fields = [
            'id', 'company', 'role', 'job_type', 'description', 'ctc', 'stipend',
            'location', 'eligible_batches', 'eligible_programmes', 'eligible_disciplines',
            'min_cpi', 'deadline', 'is_active', 'days_left', 'apply_link', 'schedules', 'created_at',
        ]

    def get_days_left(self, obj):
        from django.utils import timezone
        delta = obj.deadline - timezone.now()
        return max(0, delta.days)


class JobPostWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = JobPost
        fields = [
            'company', 'role', 'job_type', 'description', 'ctc', 'stipend',
            'location', 'eligible_batches', 'eligible_programmes', 'eligible_disciplines',
            'min_cpi', 'deadline', 'is_active', 'apply_link',
        ]


class ApplicationSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='job_post.company.name', read_only=True)
    role         = serializers.CharField(source='job_post.role', read_only=True)
    job_type     = serializers.CharField(source='job_post.job_type', read_only=True)
    deadline     = serializers.DateTimeField(source='job_post.deadline', read_only=True)

    class Meta:
        model  = PlacementApplication
        fields = ['id', 'job_post', 'company_name', 'role', 'job_type', 'deadline', 'status', 'applied_at']
        read_only_fields = ['id', 'applied_at']


class ApplicationAdminSerializer(serializers.ModelSerializer):
    roll_no      = serializers.CharField(source='student.user.username', read_only=True)
    student_name = serializers.SerializerMethodField()
    email        = serializers.CharField(source='student.user.email', read_only=True)
    company_name = serializers.CharField(source='job_post.company.name', read_only=True)
    role         = serializers.CharField(source='job_post.role', read_only=True)
    live_cpi     = serializers.SerializerMethodField()

    class Meta:
        model  = PlacementApplication
        fields = [
            'id', 'roll_no', 'student_name', 'email', 'live_cpi',
            'company_name', 'role', 'status', 'applied_at', 'updated_at',
        ]

    def get_student_name(self, obj):
        u = obj.student.user
        return f"{u.first_name} {u.last_name}".strip()

    def get_live_cpi(self, obj):
        from applications.placement_cell.selectors import get_student_published_cpi
        cpi = get_student_published_cpi(obj.student)
        return str(cpi) if cpi is not None else None


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StudentPlacementProfile
        fields = ['resume_url', 'linkedin_url', 'github_url', 'is_placed', 'opted_out', 'updated_at']
        read_only_fields = ['is_placed', 'updated_at']


class StudentAdminSerializer(serializers.ModelSerializer):
    roll_no      = serializers.CharField(source='student.user.username', read_only=True)
    student_name = serializers.SerializerMethodField()
    email        = serializers.CharField(source='student.user.email', read_only=True)
    live_cpi     = serializers.SerializerMethodField()

    class Meta:
        model  = StudentPlacementProfile
        fields = ['roll_no', 'student_name', 'email', 'live_cpi', 'resume_url', 'is_placed', 'opted_out']

    def get_student_name(self, obj):
        u = obj.student.user
        return f"{u.first_name} {u.last_name}".strip()

    def get_live_cpi(self, obj):
        from applications.placement_cell.selectors import get_student_published_cpi
        cpi = get_student_published_cpi(obj.student)
        return str(cpi) if cpi is not None else None


class AnnouncementSerializer(serializers.ModelSerializer):
    posted_by_name = serializers.SerializerMethodField()

    class Meta:
        model  = PlacementAnnouncement
        fields = ['id', 'title', 'body', 'posted_by_name', 'posted_at', 'is_pinned']
        read_only_fields = ['id', 'posted_at']

    def get_posted_by_name(self, obj):
        if obj.posted_by:
            return f"{obj.posted_by.first_name} {obj.posted_by.last_name}".strip() or obj.posted_by.username
        return None


class AnnouncementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PlacementAnnouncement
        fields = ['title', 'body', 'is_pinned']


class OffCampusPlacementSerializer(serializers.ModelSerializer):
    roll_no      = serializers.CharField(source='student.user.username', read_only=True)
    student_name = serializers.SerializerMethodField()

    class Meta:
        model  = OffCampusPlacement
        fields = [
            'id', 'roll_no', 'student_name', 'company_name', 'role',
            'offer_type', 'ctc', 'stipend', 'offer_date', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_student_name(self, obj):
        u = obj.student.user
        return f"{u.first_name} {u.last_name}".strip()


class OffCampusPlacementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OffCampusPlacement
        fields = ['student', 'company_name', 'role', 'offer_type', 'ctc', 'stipend', 'offer_date', 'notes']


class PlacementStatisticsSerializer(serializers.ModelSerializer):
    placement_rate = serializers.SerializerMethodField()

    class Meta:
        model  = PlacementStatistics
        fields = [
            'batch_year', 'total_students', 'total_placed', 'total_companies',
            'avg_ctc', 'highest_ctc', 'placement_rate', 'updated_at',
        ]

    def get_placement_rate(self, obj):
        if obj.total_students == 0:
            return 0.0
        return round(obj.total_placed / obj.total_students * 100, 1)
