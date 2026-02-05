from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.timezone import now
from django.utils import timezone
from django.db.models import Count
from .models import *
from django.http import JsonResponse
from .forms import RegisterForm
from django.contrib.auth import login, authenticate, logout
from .utils import redirect_user_by_role
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import date

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


def teacher_groups(request):
    user = request.user
    profile = user.userprofile
    grades = Grade.objects.filter(is_active = True)

    groups = ClassGroup.objects.filter(
        teacher = request.user,
        is_active = True
    ).select_related('grade')

    group_data = []

    for group in groups:
        students_count = StudentProfile.objects.filter(
            grade = group.grade
        ).count()

        session = group.sessions.last()

        present = absent = 0
        percentage = 0

        if session:
            present = session.records.filter(status='PRESENT').count()
            absent = session.records.filter(status='ABSENT').count()
            total = present + absent
            if total > 0:
                percentage = round((present / total) * 100, 1)
        
        group_data.append({
            'group': group,
            'students_count': students_count,
            'present': present,
            'absent': absent,
            'percentage': percentage
        })

    return render(request, 'teacher_groups.html', {
        'grades': grades,
        'groups': groups,
        'group_data': group_data,
        'teacher': user,
        'profile': profile
    })

def teacher_qr_attendance(request):
    return render(request, 'teacher_qr-attendance.html')

def teacher_reports(request):
    return render(request, 'teacher_reports.html')

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