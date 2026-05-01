import io
from functools import wraps

from django.http import HttpResponse
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from applications.globals.models import ExtraInfo, HoldsDesignation

from applications.placement_cell import services, selectors
from applications.placement_cell.api.serializers import (
    AnnouncementSerializer, AnnouncementWriteSerializer,
    ApplicationAdminSerializer, ApplicationSerializer,
    CompanySerializer, JobPostDetailSerializer, JobPostListSerializer,
    JobPostWriteSerializer, OffCampusPlacementSerializer,
    OffCampusPlacementWriteSerializer, PlacementScheduleSerializer,
    PlacementStatisticsSerializer, StudentAdminSerializer,
    StudentProfileSerializer,
)
from applications.placement_cell.models import (
    Company, JobPost, OffCampusPlacement, PlacementApplication, PlacementAnnouncement,
    PlacementSchedule, PlacementStatistics, StudentPlacementProfile,
)


# ─────────────────────────── helpers ────────────────────────────────────────

def role_required(allowed_roles):
    allowed_lower = {r.lower() for r in allowed_roles}

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user_roles = set(
                HoldsDesignation.objects
                .filter(user=request.user)
                .values_list('designation__name', flat=True)
            )
            user_roles_lower = {r.lower() for r in user_roles}
            if not (user_roles_lower & allowed_lower):
                return Response(
                    {'error': 'Permission denied. Required role(s): %s' % allowed_roles},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def _get_extra_info(request):
    return ExtraInfo.objects.select_related('user').get(user=request.user)


def _compute_batch_live_stats(batch_id):
    """Compute live placement statistics for a given Batch ID."""
    from django.db.models import Q
    from applications.academic_information.models import Student
    from applications.programme_curriculum.models import Batch
    from applications.placement_cell.models import PlacementResult

    try:
        batch = Batch.objects.select_related('discipline').get(pk=batch_id)
    except Batch.DoesNotExist:
        return None

    # ExtraInfo PKs for all students in this batch
    extra_ids = list(Student.objects.filter(batch_id=batch_id).values_list('id', flat=True))
    total_students = len(extra_ids)

    # Total placed (profile flag — set by both on-campus and off-campus service functions)
    total_placed = StudentPlacementProfile.objects.filter(
        student_id__in=extra_ids, is_placed=True
    ).count()

    # On-campus: distinct students with a PLACED application
    on_campus_placed = (
        PlacementApplication.objects
        .filter(student_id__in=extra_ids, status=PlacementApplication.PLACED)
        .values('student_id').distinct().count()
    )

    # Off-campus: distinct students with any OffCampusPlacement entry
    off_campus_placed = (
        OffCampusPlacement.objects
        .filter(student_id__in=extra_ids)
        .values('student_id').distinct().count()
    )

    # Companies: distinct on-campus DB companies + distinct off-campus name strings
    on_campus_cos = (
        PlacementApplication.objects
        .filter(student_id__in=extra_ids, status=PlacementApplication.PLACED)
        .values('job_post__company_id').distinct().count()
    )
    off_campus_cos = (
        OffCampusPlacement.objects
        .filter(student_id__in=extra_ids)
        .values_list('company_name', flat=True).distinct().count()
    )
    total_companies = on_campus_cos + off_campus_cos

    # CTC: from PlacementResult (on-campus) + OffCampusPlacement.ctc
    placed_app_ids = list(
        PlacementApplication.objects
        .filter(student_id__in=extra_ids, status=PlacementApplication.PLACED)
        .values_list('id', flat=True)
    )
    result_ctcs = list(
        PlacementResult.objects
        .filter(application_id__in=placed_app_ids, ctc_offered__isnull=False)
        .values_list('ctc_offered', flat=True)
    )
    offcampus_ctcs = list(
        OffCampusPlacement.objects
        .filter(student_id__in=extra_ids, ctc__isnull=False)
        .values_list('ctc', flat=True)
    )
    all_ctcs = result_ctcs + offcampus_ctcs
    avg_ctc     = str(round(sum(all_ctcs) / len(all_ctcs), 2)) if all_ctcs else None
    highest_ctc = str(max(all_ctcs)) if all_ctcs else None

    placement_rate = round(total_placed / total_students * 100, 1) if total_students > 0 else 0.0

    return {
        'batch_id':         batch.id,
        'batch_label':      str(batch),
        'batch_year':       str(batch.year),
        'total_students':   total_students,
        'total_placed':     total_placed,
        'total_companies':  total_companies,
        'avg_ctc':          avg_ctc,
        'highest_ctc':      highest_ctc,
        'placement_rate':   placement_rate,
        'on_campus_placed': on_campus_placed,
        'off_campus_placed': off_campus_placed,
    }


# ─────────────────────────── Student endpoints ──────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['student'])
def student_dashboard(request):
    extra  = _get_extra_info(request)
    jobs   = selectors.list_active_job_posts(extra)[:10]
    apps   = selectors.list_applications_for_student(extra)[:10]
    anncs  = selectors.list_announcements()[:5]
    cpi    = selectors.get_student_published_cpi(extra)

    return Response({
        'live_cpi':      str(cpi) if cpi is not None else None,
        'jobs':          JobPostListSerializer(jobs, many=True).data,
        'applications':  ApplicationSerializer(apps, many=True).data,
        'announcements': AnnouncementSerializer(anncs, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['student'])
def student_job_list(request):
    extra = _get_extra_info(request)
    jobs  = selectors.list_active_job_posts(extra)
    return Response(JobPostListSerializer(jobs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['student'])
def student_job_detail(request, job_id):
    try:
        job = selectors.get_job_post_detail(job_id)
    except JobPost.DoesNotExist:
        return Response({'error': 'Job post not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(JobPostDetailSerializer(job).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['student'])
def student_apply(request, job_id):
    extra = _get_extra_info(request)
    try:
        app = services.apply_to_job(extra, job_id)
    except JobPost.DoesNotExist:
        return Response({'error': 'Job post not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(ApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['student'])
def student_withdraw(request, app_id):
    extra = _get_extra_info(request)
    try:
        services.withdraw_application(app_id, extra)
    except PlacementApplication.DoesNotExist:
        return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'message': 'Application withdrawn.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['student'])
def student_applications(request):
    extra = _get_extra_info(request)
    apps  = selectors.list_applications_for_student(extra)
    return Response(ApplicationSerializer(apps, many=True).data)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['student'])
def student_profile(request):
    extra   = _get_extra_info(request)
    profile = selectors.get_student_profile(extra)
    cpi     = selectors.get_student_published_cpi(extra)

    if request.method == 'GET':
        data = StudentProfileSerializer(profile).data
        data['live_cpi'] = str(cpi) if cpi is not None else None
        return Response(data)

    updated = services.upsert_student_profile(extra, request.data)
    data    = StudentProfileSerializer(updated).data
    data['live_cpi'] = str(cpi) if cpi is not None else None
    return Response(data)


# ─────────────────────────── Placement Officer endpoints ────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_companies(request):
    if request.method == 'GET':
        return Response(CompanySerializer(selectors.list_companies(), many=True).data)

    serializer = CompanySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    company = services.create_company(serializer.validated_data)
    return Response(CompanySerializer(company).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_company_detail(request, company_id):
    try:
        company = Company.objects.get(pk=company_id)
    except Company.DoesNotExist:
        return Response({'error': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(CompanySerializer(company).data)
    if request.method == 'DELETE':
        services.delete_company(company_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CompanySerializer(company, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    updated = services.update_company(company_id, serializer.validated_data)
    return Response(CompanySerializer(updated).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_jobs(request):
    if request.method == 'GET':
        return Response(JobPostListSerializer(selectors.list_job_posts_admin(), many=True).data)

    serializer = JobPostWriteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    job = services.create_job_post(serializer.validated_data, request.user)
    return Response(JobPostDetailSerializer(job).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_job_detail(request, job_id):
    try:
        job = selectors.get_job_post_detail(job_id)
    except JobPost.DoesNotExist:
        return Response({'error': 'Job post not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(JobPostDetailSerializer(job).data)

    serializer = JobPostWriteSerializer(job, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    updated = services.update_job_post(job_id, serializer.validated_data)
    return Response(JobPostDetailSerializer(updated).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_job_toggle(request, job_id):
    try:
        job = services.toggle_job_post_active(job_id)
    except JobPost.DoesNotExist:
        return Response({'error': 'Job post not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'id': job.id, 'is_active': job.is_active})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_applicants(request, job_id):
    apps = selectors.list_applications_for_job_post(job_id)
    return Response(ApplicationAdminSerializer(apps, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_app_status(request, app_id):
    new_status = request.data.get('status')
    if not new_status:
        return Response({'error': 'status is required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        app = services.update_application_status(app_id, new_status)
    except PlacementApplication.DoesNotExist:
        return Response({'error': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(ApplicationAdminSerializer(app).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_bulk_status(request):
    ids        = request.data.get('ids', [])
    new_status = request.data.get('status')
    if not ids or not new_status:
        return Response({'error': 'ids and status are required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        count = services.bulk_update_application_status(ids, new_status)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'updated': count})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_batches(request):
    """
    Returns all batches that have at least one published ResultAnnouncement.
    Used to populate the batch filter dropdown on the Students tab.
    """
    from applications.examination.models import ResultAnnouncement
    from applications.programme_curriculum.models import Batch

    batch_ids = (
        ResultAnnouncement.objects
        .filter(announced=True)
        .values_list('batch_id', flat=True)
        .distinct()
    )
    batches = (
        Batch.objects
        .filter(id__in=batch_ids)
        .select_related('discipline')
        .order_by('-year', 'name')
    )
    return Response([
        {'id': b.id, 'label': str(b), 'year': b.year}
        for b in batches
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_students(request):
    """
    Returns students for a given batch_id whose published final CPI is available.
    Requires ?batch_id= query param. Without it returns empty list.
    """
    from applications.academic_information.models import Student
    from applications.examination.models import ResultAnnouncement
    from applications.placement_cell.selectors import get_student_published_cpi

    batch_id = request.query_params.get('batch_id')
    if not batch_id:
        return Response([])

    students = Student.objects.filter(batch_id=batch_id).select_related('id__user')

    has_published = ResultAnnouncement.objects.filter(batch_id=batch_id, announced=True).exists()
    if not has_published:
        return Response([])

    # Batch-fetch off-campus placements for all students in this batch
    extra_pks = [stu.pk for stu in students]
    offcampus_map = {}
    for ocp in OffCampusPlacement.objects.filter(student_id__in=extra_pks).select_related('student'):
        offcampus_map.setdefault(ocp.student_id, []).append(ocp.company_name)

    results = []
    for stu in students:
        extra = stu.id  # ExtraInfo
        cpi = get_student_published_cpi(extra)
        if cpi is None:
            continue

        try:
            profile = StudentPlacementProfile.objects.get(student=extra)
            is_placed  = profile.is_placed
            opted_out  = profile.opted_out
            resume_url = profile.resume_url
        except StudentPlacementProfile.DoesNotExist:
            is_placed  = False
            opted_out  = False
            resume_url = ''

        off_campus = offcampus_map.get(extra.pk, [])
        results.append({
            'roll_no':      extra.user.username,
            'student_name': f"{extra.user.first_name} {extra.user.last_name}".strip(),
            'email':        extra.user.email,
            'live_cpi':     str(cpi),
            'is_placed':    is_placed,
            'opted_out':    opted_out,
            'resume_url':   resume_url,
            'off_campus':   off_campus,
        })

    return Response(results)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_export(request):
    try:
        import openpyxl
    except ImportError:
        return Response({'error': 'openpyxl not installed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    rows = selectors.export_placement_data_rows()
    wb   = openpyxl.Workbook()
    ws   = wb.active
    ws.title = 'Placement Data'

    headers = ['Roll No', 'Name', 'Email', 'Company', 'Role', 'Job Type', 'Status', 'Applied At']
    ws.append(headers)
    for row in rows:
        ws.append([row.get(k, '') for k in ['roll_no', 'name', 'email', 'company', 'role', 'job_type', 'status', 'applied_at']])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="placement_data.xlsx"'
    return response


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_announcements(request):
    if request.method == 'GET':
        return Response(AnnouncementSerializer(selectors.list_announcements(), many=True).data)

    serializer = AnnouncementWriteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    announcement = services.create_announcement(serializer.validated_data, request.user)
    return Response(AnnouncementSerializer(announcement).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_announcement_delete(request, ann_id):
    services.delete_announcement(ann_id)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_statistics(request):
    batch_id = request.query_params.get('batch_id')
    if batch_id:
        data = _compute_batch_live_stats(batch_id)
        if data is None:
            return Response({'error': 'Batch not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(data)
    stats = selectors.get_placement_statistics()
    return Response(PlacementStatisticsSerializer(stats, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_statistics_refresh(request):
    batch_year = request.data.get('batch_year')
    if not batch_year:
        return Response({'error': 'batch_year is required.'}, status=status.HTTP_400_BAD_REQUEST)
    stats = services.refresh_statistics(batch_year)
    return Response(PlacementStatisticsSerializer(stats).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_student_update(request):
    """Manually update a student's placement profile fields (is_placed, opted_out)."""
    roll_no = request.data.get('roll_no', '').strip()
    if not roll_no:
        return Response({'error': 'roll_no is required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        extra = ExtraInfo.objects.get(user__username=roll_no)
    except ExtraInfo.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    profile, _ = StudentPlacementProfile.objects.get_or_create(student=extra)

    if 'is_placed' in request.data:
        profile.is_placed = bool(request.data['is_placed'])
    # opted_out can only be set to True via API (reverting requires office visit)
    if request.data.get('opted_out') is True:
        profile.opted_out = True
    profile.save()

    return Response({'roll_no': roll_no, 'is_placed': profile.is_placed, 'opted_out': profile.opted_out})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_offcampus(request):
    if request.method == 'GET':
        placements = OffCampusPlacement.objects.select_related('student__user').all()
        return Response(OffCampusPlacementSerializer(placements, many=True).data)

    roll_no = request.data.get('roll_no', '').strip()
    if not roll_no:
        return Response({'error': 'roll_no is required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        student = ExtraInfo.objects.get(user__username=roll_no)
    except ExtraInfo.DoesNotExist:
        return Response({'error': f'No student found with roll number {roll_no}.'}, status=status.HTTP_400_BAD_REQUEST)

    payload = {k: v for k, v in request.data.items() if k != 'roll_no'}
    payload['student'] = student.pk
    serializer = OffCampusPlacementWriteSerializer(data=payload)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    placement = services.add_offcampus_placement(serializer.validated_data, request.user)
    return Response(OffCampusPlacementSerializer(placement).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement officer'])
def officer_offcampus_detail(request, ocp_id):
    services.delete_offcampus_placement(ocp_id)
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────── Placement Chairman endpoints ───────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement chairman'])
def chairman_statistics(request):
    batch_id = request.query_params.get('batch_id')
    if batch_id:
        data = _compute_batch_live_stats(batch_id)
        if data is None:
            return Response({'error': 'Batch not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(data)
    stats = selectors.get_placement_statistics()
    return Response(PlacementStatisticsSerializer(stats, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement chairman'])
def chairman_batches(request):
    from applications.examination.models import ResultAnnouncement
    from applications.programme_curriculum.models import Batch

    batch_ids = (
        ResultAnnouncement.objects
        .filter(announced=True)
        .values_list('batch_id', flat=True)
        .distinct()
    )
    batches = (
        Batch.objects
        .filter(id__in=batch_ids)
        .select_related('discipline')
        .order_by('-year', 'name')
    )
    return Response([
        {'id': b.id, 'label': str(b), 'year': b.year}
        for b in batches
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement chairman'])
def chairman_students(request):
    from applications.academic_information.models import Student
    from applications.examination.models import ResultAnnouncement
    from applications.placement_cell.selectors import get_student_published_cpi

    batch_id = request.query_params.get('batch_id')
    if not batch_id:
        return Response([])

    students = Student.objects.filter(batch_id=batch_id).select_related('id__user')

    has_published = ResultAnnouncement.objects.filter(batch_id=batch_id, announced=True).exists()
    if not has_published:
        return Response([])

    extra_pks = [stu.pk for stu in students]
    offcampus_map = {}
    for ocp in OffCampusPlacement.objects.filter(student_id__in=extra_pks):
        offcampus_map.setdefault(ocp.student_id, []).append(ocp.company_name)

    results = []
    for stu in students:
        extra = stu.id
        cpi = get_student_published_cpi(extra)
        if cpi is None:
            continue

        try:
            profile = StudentPlacementProfile.objects.get(student=extra)
            is_placed  = profile.is_placed
            opted_out  = profile.opted_out
            resume_url = profile.resume_url
        except StudentPlacementProfile.DoesNotExist:
            is_placed  = False
            opted_out  = False
            resume_url = ''

        off_campus = offcampus_map.get(extra.pk, [])
        results.append({
            'roll_no':      extra.user.username,
            'student_name': f"{extra.user.first_name} {extra.user.last_name}".strip(),
            'email':        extra.user.email,
            'live_cpi':     str(cpi),
            'is_placed':    is_placed,
            'opted_out':    opted_out,
            'resume_url':   resume_url,
            'off_campus':   off_campus,
        })

    return Response(results)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(['placement chairman'])
def chairman_export(request):
    try:
        import openpyxl
    except ImportError:
        return Response({'error': 'openpyxl not installed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    rows = selectors.export_placement_data_rows()
    wb   = openpyxl.Workbook()
    ws   = wb.active
    ws.title = 'Placement Data'

    headers = ['Roll No', 'Name', 'Email', 'Company', 'Role', 'Job Type', 'Status', 'Applied At']
    ws.append(headers)
    for row in rows:
        ws.append([row.get(k, '') for k in ['roll_no', 'name', 'email', 'company', 'role', 'job_type', 'status', 'applied_at']])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="placement_data_full.xlsx"'
    return response


# ─────────────────────────── Dean / Faculty endpoints ───────────────────────

DEAN_ROLES = ['Dean Academic', 'dean', 'Associate Professor', 'Professor', 'Assistant Professor']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(DEAN_ROLES)
def dean_batches(request):
    from applications.examination.models import ResultAnnouncement
    from applications.programme_curriculum.models import Batch

    batch_ids = (
        ResultAnnouncement.objects
        .filter(announced=True)
        .values_list('batch_id', flat=True)
        .distinct()
    )
    batches = Batch.objects.filter(id__in=batch_ids).select_related('discipline').order_by('-year', 'name')
    return Response([{'id': b.id, 'label': str(b), 'year': b.year} for b in batches])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(DEAN_ROLES)
def dean_statistics(request):
    batch_id = request.query_params.get('batch_id')
    if batch_id:
        data = _compute_batch_live_stats(batch_id)
        if data is None:
            return Response({'error': 'Batch not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(data)
    stats = selectors.get_placement_statistics()
    return Response(PlacementStatisticsSerializer(stats, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@role_required(DEAN_ROLES)
def dean_announcements(request):
    return Response(AnnouncementSerializer(selectors.list_announcements(), many=True).data)
