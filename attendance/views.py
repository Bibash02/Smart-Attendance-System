from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.timezone import now
from .models import *
from django.http import JsonResponse
from .forms import RegisterForm
from django.contrib.auth import login, authenticate, logout
from .utils import redirect_user_by_role
from django.views.decorators.csrf import csrf_exempt
import json

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

def student_dashboard(request):
    pass