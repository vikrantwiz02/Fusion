from django.conf.urls import url

from . import views

urlpatterns = [
    # ── Student ──────────────────────────────────────────────────────────────
    url(r'^api/stu/dashboard/$',                    views.student_dashboard,    name='pc-stu-dashboard'),
    url(r'^api/stu/jobs/$',                         views.student_job_list,     name='pc-stu-jobs'),
    url(r'^api/stu/jobs/(?P<job_id>\d+)/$',         views.student_job_detail,   name='pc-stu-job-detail'),
    url(r'^api/stu/jobs/(?P<job_id>\d+)/apply/$',   views.student_apply,        name='pc-stu-apply'),
    url(r'^api/stu/applications/$',                 views.student_applications, name='pc-stu-applications'),
    url(r'^api/stu/applications/(?P<app_id>\d+)/withdraw/$', views.student_withdraw, name='pc-stu-withdraw'),
    url(r'^api/stu/profile/$',                      views.student_profile,      name='pc-stu-profile'),

    # ── Placement Officer ────────────────────────────────────────────────────
    url(r'^api/officer/companies/$',                        views.officer_companies,         name='pc-ofc-companies'),
    url(r'^api/officer/companies/(?P<company_id>\d+)/$',    views.officer_company_detail,    name='pc-ofc-company-detail'),
    url(r'^api/officer/jobs/$',                             views.officer_jobs,              name='pc-ofc-jobs'),
    url(r'^api/officer/jobs/(?P<job_id>\d+)/$',             views.officer_job_detail,        name='pc-ofc-job-detail'),
    url(r'^api/officer/jobs/(?P<job_id>\d+)/toggle/$',      views.officer_job_toggle,        name='pc-ofc-job-toggle'),
    url(r'^api/officer/jobs/(?P<job_id>\d+)/applicants/$',  views.officer_applicants,        name='pc-ofc-applicants'),
    url(r'^api/officer/applications/(?P<app_id>\d+)/status/$', views.officer_app_status,    name='pc-ofc-app-status'),
    url(r'^api/officer/applications/bulk-status/$',         views.officer_bulk_status,       name='pc-ofc-bulk-status'),
    url(r'^api/officer/batches/$',                           views.officer_batches,           name='pc-ofc-batches'),
    url(r'^api/officer/students/$',                         views.officer_students,          name='pc-ofc-students'),
    url(r'^api/officer/students/update/$',                  views.officer_student_update,    name='pc-ofc-student-update'),
    url(r'^api/officer/export/$',                           views.officer_export,            name='pc-ofc-export'),
    url(r'^api/officer/announcements/$',                    views.officer_announcements,     name='pc-ofc-announcements'),
    url(r'^api/officer/announcements/(?P<ann_id>\d+)/$',    views.officer_announcement_delete, name='pc-ofc-announcement-delete'),
    url(r'^api/officer/statistics/$',                       views.officer_statistics,        name='pc-ofc-statistics'),
    url(r'^api/officer/statistics/refresh/$',               views.officer_statistics_refresh, name='pc-ofc-statistics-refresh'),
    url(r'^api/officer/offcampus/$',                        views.officer_offcampus,         name='pc-ofc-offcampus'),
    url(r'^api/officer/offcampus/(?P<ocp_id>\d+)/$',        views.officer_offcampus_detail,  name='pc-ofc-offcampus-detail'),

    # ── Placement Chairman ───────────────────────────────────────────────────
    url(r'^api/chairman/statistics/$',  views.chairman_statistics, name='pc-chm-statistics'),
    url(r'^api/chairman/batches/$',     views.chairman_batches,    name='pc-chm-batches'),
    url(r'^api/chairman/students/$',    views.chairman_students,   name='pc-chm-students'),
    url(r'^api/chairman/export/$',      views.chairman_export,     name='pc-chm-export'),

    # ── Dean / Faculty ───────────────────────────────────────────────────────
    url(r'^api/dean/batches/$',        views.dean_batches,        name='pc-dean-batches'),
    url(r'^api/dean/statistics/$',     views.dean_statistics,     name='pc-dean-statistics'),
    url(r'^api/dean/announcements/$',  views.dean_announcements,  name='pc-dean-announcements'),
]
