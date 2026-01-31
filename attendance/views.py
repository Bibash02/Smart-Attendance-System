from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from .models import *

# Create your views here.
def teacher_dashboard(request):
    if request.user.userprofile.role != 'TEACHER':
        return redirect('login')

    today = now().date()

    classes = ClassGroup.objects.filter(
        teacher = request.user,
        is_active = True
    )

    active_groups = classes.count()

    total_students = StudentEnrollment.objects.filter(
        class_group__in = classes
    ).values('student').distinct().count()

    total_records = AttendanceRecord.objects.filter(
        session__class_group__in = classes
    ).count()

    present_records = AttendanceRecord.objects.filter(
        session__class_group__in = classes,
        status = 'PRESENT'
    ).count()

    avg_attendance = (
        (present_records / total_records) * 100
        if total_records > 0 else 0
    )

    sessions_today = AttendanceSession.objects.filter(
        class_group__in = classes,
    ).count()

    pending_today = classes.exclude(
        id__in = sessions_today
    ).count()

    context = {
        'active_groups': active_groups,
        'total_students': total_students,
        'avg_attendace': avg_attendance,
        'pending_today': pending_today,
        'classes': classes
    }

    return render(request, 'teacher_dashboard.html', context)

def create_attendace_session(request, class_id):
    class_group = get_object_or_404(
        ClassGroup, id = class_id, teacher = request.user
    )

    session, created = AttendanceSession.objects.get_or_create(
        class_group = class_group,
        date = now().date(),
        defaults={'created_by': request.user}
    )

    return redirect('mark_attendace', session.id)

def mark_attendance(request, session_id):
    session = get_object_or_404(
        AttendanceSession, id = session_id, created_by = request.user
    )

    students = StudentEnrollment.objects.filter(
        class_group = session.class_group
    )

    if request.method == 'POST':
        for enrollment in students:
            status = request.post.get(str(enrollment.student.id))
            AttendanceRecord.objects.update_or_create(
                session = session,
                student = enrollment.student,
                defaults={'status': status}
            )
        return redirect('teacher_dashboard')
    return render(request, 'mark_attendance.html', {
        'session': session,
        'students': students
    })

def student_dashboard(request):
    if request.user.userprofile.role != 'STUDENT':
        return redirect('login')
    
    student = request.user.userprofle

    records = AttendanceRecord.objects.filter(
        student = student,
    ).select_related('session', 'session__class_group')

    return render(request, 'student_dashboard.html', {
        'records': records
    })

def groups(request):
    return render(request, 'groups.html')

def qr_attendance(request):
    return render(request, 'qr-attendance.html')

def reports(request):
    return render(request, 'reports.html')