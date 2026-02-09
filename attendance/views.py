from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.timezone import now
from django.utils import timezone
from django.db.models import Count, Q
from .models import *
from django.http import JsonResponse
from .forms import RegisterForm
from django.contrib.auth import login, authenticate, logout
from .utils import redirect_user_by_role
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import HttpResponseForbidden
from datetime import date, datetime, timedelta
from calendar import monthrange
from django.db import transaction
from django.urls import reverse


# Create your views here.
def auth(request):
    return render(request, 'signin.html')

def register_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        role = request.POST.get("role")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            return render(request, 'signin.html', {
                "reg_error": "Passwords do not match"
            })

        if User.objects.filter(email=email).exists():
            return render(request, 'signin.html', {
                "reg_error": "Email already exists"
            })

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )

        UserProfile.objects.create(
            user=user,
            role=role
        )

        return redirect('signin')

    return redirect('signin')

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(
                request,
                username=user_obj.username,
                password=password
            )
        except User.DoesNotExist:
            user = None

        if user:
            login(request, user)

            role = user.userprofile.role
            if role == "TEACHER":
                return redirect('teacher_dashboard')
            elif role == "STUDENT":
                return redirect('student_dashboard')

        return render(request, 'signin.html', {
            "login_error": "Invalid email or password"
        })

    return redirect('signin')

def logout_view(request):
    logout(request)
    return redirect('login')

def forgot_password(request):
    pass

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
        session__class_group__in=classes,
        status='PRESENT'
    ).count()

    avg_attendance = round(
        (present_records / total_records) * 100, 2
    ) if total_records > 0 else 0

    # Sessions created TODAY
    sessions_today = AttendanceSession.objects.filter(
        class_group__in=classes,
        date=today
    )

    # Classes that already have attendance today
    classes_with_attendance = sessions_today.values_list(
        'class_group_id', flat=True
    )

    # Pending = classes WITHOUT attendance today
    pending_today = classes.exclude(
        id__in=classes_with_attendance
    ).count()

    context = {
        'active_groups': active_groups,
        'total_students': total_students,
        'avg_attendace': avg_attendance,
        'pending_today': pending_today,
        'classes': classes,
        'teacher': request.user,
        'profile': request.user.userprofile,
        'now': now()
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

def teacher_mark_attendance(request, session_id):
    teacher = request.user

    groups = ClassGroup.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related('subject', 'grade')

    selected_group = None
    students = []

    group_id = request.GET.get('group')

    if group_id:
        selected_group = get_object_or_404(
            ClassGroup,
            id=group_id,
            teacher=teacher
        )

        students = StudentProfile.objects.filter(
            grade=selected_group.grade
        ).select_related('user')

    context = {
        'groups': groups,
        'selected_group': selected_group,
        'students': students,
        'today': date.today(),
    }

    return render(request, 'teacher_mark_attendance.html', context)

def mark_attendance(request, group_id):
    group = get_object_or_404(ClassGroup, id=group_id)

    students = StudentProfile.objects.filter(
        class_group=group,
        is_active=True
    ).order_by('roll_no')

    # ---------------------------
    # MONTH HANDLING
    # ---------------------------
    selected_month = request.GET.get('month') or request.POST.get('month')

    if selected_month:
        year, month = map(int, selected_month.split('-'))
    else:
        today = date.today()
        year, month = today.year, today.month

    # All dates of the month
    total_days = monthrange(year, month)[1]
    dates = [date(year, month, d) for d in range(1, total_days + 1)]

    # ---------------------------
    # ATTENDANCE RECORDS
    # ---------------------------
    records = Attendance.objects.filter(
        group=group,
        date__year=year,
        date__month=month
    )

    saved_dates = set(
        records.values_list('date', flat=True)
    )

    # 🔥 FIND ACTIVE DATE (FIRST UNSAVED DAY)
    active_date = None
    for d in dates:
        if d not in saved_dates:
            active_date = d
            break

    # If everything is saved, lock the month
    already_saved = active_date is None

    # ---------------------------
    # SAVE ATTENDANCE
    # ---------------------------
    if request.method == 'POST':

        if already_saved:
            return HttpResponseForbidden("Attendance already locked")

        with transaction.atomic():
            for student in students:
                key = f"attendance_{student.id}_{active_date}"
                status = request.POST.get(key)

                if status:
                    Attendance.objects.update_or_create(
                        student=student,
                        group=group,
                        date=active_date,
                        defaults={
                            'status': status,
                            'is_locked': True
                        }
                    )

        # 🔁 AUTO MOVE TO NEXT DAY
        return redirect(
            f"{request.path}?month={year}-{month:02d}"
        )

    context = {
        'group': group,
        'students': students,
        'dates': dates,
        'records': records,
        'active_date': active_date,
        'already_saved': already_saved,
        'selected_month': f"{year}-{month:02d}",
    }

    return render(request, 'mark_attendance.html', context)

@login_required
def add_student(request, group_id):
    if request.method != 'POST':
        return redirect('mark_attendance', group_id=group_id)

    group = get_object_or_404(ClassGroup, id=group_id)

    name = request.POST.get('student_name')
    student_id = request.POST.get('student_id')
    email = request.POST.get('student_email')

    if StudentProfile.objects.filter(student_id=student_id).exists():
        messages.error(request, 'Student ID already exists')
        return redirect('mark_attendance', group_id=group.id)

    user = User.objects.create_user(
        username=student_id,
        email=email,
        password='student123'
    )
    user.first_name = name
    user.save()

    student = StudentProfile.objects.create(
        user=user,
        grade=group.grade,
        student_id=student_id,
        class_group=group,
        roll_no=StudentProfile.objects.filter(class_group=group).count() + 1
    )

    StudentEnrollment.objects.create(
        student=student,
        class_group=group
    )

    messages.success(request, 'Student added successfully')

    return redirect('mark_attendance', group_id=group.id)

def save_attendance(request, group, year, month):
    today = now().date()

    session, _ = AttendanceSession.objects.get_or_create(
        class_group=group,
        date=today,
        defaults={'marked_by': request.user}
    )

    for key, value in request.POST.items():
        if not key.startswith('attendance_'):
            continue

        _, student_id, date_str = key.split('_')
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # VERY IMPORTANT: skip other dates
        if attendance_date != today:
            continue

        try:
            student = StudentProfile.objects.get(
                id=student_id,
                class_group=group
            )

            AttendanceRecord.objects.update_or_create(
                session=session,
                student=student,
                defaults={'status': value}
            )

        except StudentProfile.DoesNotExist:
            continue

    messages.success(request, "Today's attendance saved successfully")

    return redirect(
        reverse('mark_attendance', args=[group.id]) +
        f'?month={year}-{month:02d}'
    )

@login_required
def attendance_report(request, group_id):
    """Generate attendance report for a group"""
    group = get_object_or_404(ClassGroup, id=group_id)
    
    # Get date range
    selected_month = request.GET.get('month')
    if selected_month:
        year, month = map(int, selected_month.split('-'))
    else:
        year, month = datetime.now().year, datetime.now().month
    
    num_days = monthrange(year, month)[1]
    start_date = datetime(year, month, 1).date()
    end_date = datetime(year, month, num_days).date()
    
    students = StudentProfile.objects.filter(
        class_group=group,
        is_active=True
    ).select_related('user', 'grade').order_by('roll_no')
    
    # Get all sessions for this month
    sessions = AttendanceSession.objects.filter(
        class_group=group,
        date__range=[start_date, end_date]
    ).prefetch_related('records')
    
    # Calculate statistics for each student
    student_stats = []
    for student in students:
        present_count = 0
        absent_count = 0
        late_count = 0
        total_sessions = 0
        
        for session in sessions:
            total_sessions += 1
            try:
                record = session.records.get(student=student)
                if record.status == 'PRESENT':
                    present_count += 1
                elif record.status == 'ABSENT':
                    absent_count += 1
                elif record.status == 'LATE':
                    late_count += 1
            except AttendanceRecord.DoesNotExist:
                # No record means absent
                absent_count += 1
        
        # Calculate attendance percentage
        attendance_percentage = (present_count / total_sessions * 100) if total_sessions > 0 else 0
        
        student_stats.append({
            'student': student,
            'total_sessions': total_sessions,
            'present': present_count,
            'absent': absent_count,
            'late': late_count,
            'percentage': round(attendance_percentage, 2)
        })
    
    context = {
        'group': group,
        'student_stats': student_stats,
        'selected_month': f"{year}-{month:02d}",
        'month_name': datetime(year, month, 1).strftime('%B %Y'),
        'total_sessions': sessions.count()
    }
    
    return render(request, 'report.html', context)

@login_required
def group_list(request):
    """List all class groups for the teacher"""
    if request.user.is_staff or request.user.is_superuser:
        groups = ClassGroup.objects.filter(is_active=True).select_related('subject', 'grade', 'teacher')
    else:
        groups = ClassGroup.objects.filter(
            teacher=request.user,
            is_active=True
        ).select_related('subject', 'grade')
    
    context = {
        'groups': groups
    }
    
    return render(request, 'group_list.html', context)

def teacher_groups(request):
    user = request.user
    profile = user.userprofile
    grades = Grade.objects.filter(is_active=True)

    groups = ClassGroup.objects.filter(
        teacher=user,
        is_active=True
    ).select_related('subject', 'grade')

    group_data = []

    for group in groups:
        # Correct student count
        students_count = StudentProfile.objects.filter(
            class_group=group,
            is_active=True
        ).count()

        last_date = Attendance.objects.filter(group=group).aggregate(
            last_date=models.Max('date')
        )['last_date']

        if last_date:
            present = Attendance.objects.filter(group=group, date=last_date, status='PRESENT').count()
            absent = Attendance.objects.filter(group=group, date=last_date, status='ABSENT').count()
            total = Attendance.objects.filter(group=group, date=last_date).count()
            percentage = round((present / total) * 100, 1) if total > 0 else 0
        else:
            present = absent = percentage = 0

        group_data.append({
            'group': group,
            'students_count': students_count,
            'present': present,
            'absent': absent,
            'percentage': percentage
        })

    context = {
        'grades': grades,
        'groups': groups,
        'group_data': group_data,
        'teacher': user,
        'profile': profile
    }

    return render(request, 'teacher_groups.html', context)

def teacher_qr_attendance(request):
    return render(request, 'teacher_qr-attendance.html')

def teacher_reports(request):
    teacher = request.user
    grades = Grade.objects.filter(is_active=True)

    records = Attendance.objects.filter(
        group__teacher=teacher
    ).select_related('student', 'group')

    # ===== TOP STATS =====
    total_present = records.filter(status='PRESENT').count()
    total_absent = records.filter(status='ABSENT').count()
    total_late = records.filter(status='LATE').count()

    total_classes = records.count()
    overall_rate = round((total_present / total_classes) * 100, 1) if total_classes > 0 else 0

    # ===== STUDENT REPORT =====
    student_reports = records.values(
        'student__id',
        'student__user__first_name',
        'student__user__last_name',
        'student__roll_no',
        'group__subject__name',
        'group__grade__name'
    ).annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status='PRESENT')),
        absent=Count('id', filter=Q(status='ABSENT')),
        late=Count('id', filter=Q(status='LATE')),
    )

    for s in student_reports:
        s['percentage'] = round(
            (s['present'] / s['total']) * 100, 1
        ) if s['total'] > 0 else 0

    context = {
        'total_present': total_present,
        'total_absent': total_absent,
        'total_late': total_late,
        'overall_rate': overall_rate,
        'student_reports': student_reports,
        'grades': grades
    }

    return render(request, 'teacher_reports.html', context)

def student_dashboard(request):
    user = request.user
    profile = user.userprofile

    context = {
        'user': user,
        'profile': profile,
    }

    return render(request, 'student_dashboard.html', context)

def student_attendance(request):
    return render(request, 'student-attendance.html')

def student_class_schedule(request):
    return render(request, 'student_class_schedule.html')

def student_mark_attendance(request):
    return render(request, 'student_mark_attendance.html')

def student_profile(request):
    user = request.user
    profile = UserProfile.objects.get(user=user)

    # ---- Attendance Percentage ----
    total_records = AttendanceRecord.objects.filter(
        student__user=user
    ).count()

    present_records = AttendanceRecord.objects.filter(
        student__user=user,
        status='PRESENT'
    ).count()

    attendance_percentage = (
        round((present_records / total_records) * 100, 2)
        if total_records > 0 else 0
    )

    # ---- Subjects Count ----
    subjects_count = ClassGroup.objects.filter(
        studentprofile__user=user,
        is_active=True
    ).distinct().count()

    # ---- Day Streak (simple version) ----
    today = timezone.now().date()
    streak = 0

    for i in range(0, 30):
        date = today - timezone.timedelta(days=i)
        if AttendanceRecord.objects.filter(
            student__user=user,
            session__date=date,
            status='PRESENT'
        ).exists():
            streak += 1
        else:
            break

    context = {
        'user': user,
        'profile': profile,
        'attendance_percentage': attendance_percentage,
        'subjects_count': subjects_count,
        'day_streak': streak,
    }

    return render(request, 'student_profile.html', context)

def student_profile_edit(request):
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)

    if request.method == "POST":
        # Update basic user info
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.email = request.POST.get("email", user.email)
        user.save()

        # Update profile info
        profile.phone = request.POST.get("phone", profile.phone)
        profile.role = request.POST.get("role", profile.role)

        # Handle profile image if uploaded
        if "profile_image" in request.FILES:
            profile.profile_image = request.FILES["profile_image"]

        profile.save()

        return redirect("student_profile")  # redirect safely

    return render(request, "student_profile_edit.html", {
        "user": user,
        "profile": profile
    })