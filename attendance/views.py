from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.timezone import now
from django.utils import timezone
from django.db.models import Count, Q
from .models import *
from django.http import JsonResponse
from .forms import *
from django.contrib.auth import login, authenticate, logout
from .utils import redirect_user_by_role
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import HttpResponseForbidden
from datetime import date, datetime, timedelta
from calendar import monthrange
from django.db import transaction
from django.urls import reverse
from calendar import monthrange
import re

# Create your views here.
def auth(request):
    return render(request, 'signin.html')

# def auth_page(request):
#     class_groups = ClassGroup.objects.all()
#     return render(request, "signin.html", {
#         "class_groups": class_groups
#     })

# def teacher_register(request):
#     if request.method == "POST":
#         name = request.POST.get("name")
#         email = request.POST.get("email")
#         password = request.POST.get("password")
#         confirm_password = request.POST.get("confirm_password")

#         if password != confirm_password:
#             messages.error(request, "Passwords do not match.")
#             return redirect("auth_page")

#         if User.objects.filter(username=email).exists():
#             messages.error(request, "Email already exists.")
#             return redirect("auth_page")

#         # Create User
#         user = User.objects.create_user(
#             username=email,
#             email=email,
#             password=password,
#             first_name=name
#         )

#         # Create UserProfile
#         UserProfile.objects.create(user=user, role="TEACHER")

#         messages.success(request, "Teacher registered successfully. You can now login.")
#         return redirect("auth_page")

#     return redirect("auth_page")

# def student_register(request):
#     if request.method == "POST":
#         full_name = request.POST.get("full_name")
#         email = request.POST.get("email").strip().lower()
#         student_id = request.POST.get("student_id")
#         class_group_id = request.POST.get("class_group")
#         password = request.POST.get("password")
#         confirm_password = request.POST.get("confirm_password")

#         if password != confirm_password:
#             messages.error(request, "Passwords do not match.")
#             return redirect("auth_page")

#         # Check student exists (created by teacher)
#         try:
#             student = StudentProfile.objects.get(
#                 student_id=student_id,
#                 class_group_id=class_group_id,
#                 is_active=True
#             )
#         except StudentProfile.DoesNotExist:
#             messages.error(request, "Student not found. Contact your teacher.")
#             return redirect("auth_page")

#         # Prevent double registration
#         if student.user:
#             messages.error(request, "Already registered.")
#             return redirect("auth_page")

#         # Prevent duplicate email
#         if User.objects.filter(username=email).exists():
#             messages.error(request, "Email already registered.")
#             return redirect("auth_page")

#         # Create user account
#         user = User.objects.create_user(
#             username=email.strip().lower(),   # IMPORTANT: use email as username
#             email=email.strip().lower(),
#             password=password,
#             first_name=full_name
#         )

#         # Assign role
#         UserProfile.objects.create(user=user, role="STUDENT")

#         # Link student profile
#         student.user = user
#         student.save()

#         messages.success(request, "Registration successful. Please login.")
#         return redirect("auth_page")

#     return redirect("auth_page")

def register_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        role = request.POST.get("role")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        # 🔹 Empty fields check
        if not name or not email or not password or not confirm:
            messages.error(request, "All fields are required")
            return redirect('signin')

        # 🔹 Email validation
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email format")
            return redirect('signin')

        # 🔹 Password match check
        if password != confirm:
            messages.error(request, "Passwords do not match")
            return redirect('signin')

        # 🔹 Simple password length validation
        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters")
            return redirect('signin')

        # 🔹 Email uniqueness check
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect('signin')

        # 🔹 Create user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )

        # 🔹 Create profile
        UserProfile.objects.create(
            user=user,
            role=role
        )

        messages.success(request, "Registration successful! Please login.")
        return redirect('signin')

    return redirect('signin')

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Try to get the user by email
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Invalid email or password.")
            return redirect('auth_page')

        # Authenticate using username (email used as username)
        user = authenticate(request, username=user_obj.username, password=password)

        if user is None:
            messages.error(request, "Invalid email or password.")
            return redirect('auth_page')

        login(request, user)

        # Check role safely
        if hasattr(user, 'userprofile'):
            role = user.userprofile.role.strip().upper()
            if role == "TEACHER":
                return redirect('teacher_dashboard')
            elif role == "STUDENT":
                return redirect('student_dashboard')
            elif role == "ADMIN":
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Role not assigned properly.")
                return redirect('auth_page')
        else:
            messages.error(request, "UserProfile not found. Contact admin.")
            return redirect('auth_page')

    return redirect('auth_page')

def logout_view(request):
    logout(request)
    return redirect('login')

def forgot_password(request):
    pass

def teacher_dashboard(request):
    if request.user.userprofile.role != 'TEACHER':
        return redirect('login')

    teacher = request.user
    today = now().date()
    week_start = today - timedelta(days=6)

    groups = ClassGroup.objects.filter(teacher = teacher, is_active = True).select_related('subject', 'grade')

    today_classes = []

    for group in groups:
        student_count = StudentProfile.objects.filter(class_group = group, is_active = True).count()

        # check if attendance is marked today
        marked_today = Attendance.objects.filter(group = group, date = today).exists()

        # weekly attendance
        week_records = Attendance.objects.filter(group = group, date__range = [week_start, today])

        present = week_records.filter(status = 'PRESENT').count()
        total = week_records.count()

        percentage = round((present / total) * 100, 1) if total > 0 else 0

        today_classes.append({
            'group': group,
            'student_count': student_count,
            'percentage': percentage,
            'status': 'Completed' if marked_today else 'Pending'
        })

    classes = ClassGroup.objects.filter(
        teacher = request.user,
        is_active = True
    )

    active_groups = classes.count()

    total_assignments = Assignment.objects.filter(
        teacher = teacher
    ).count()

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

    today_assignments = Assignment.objects.filter(teacher = request.user).order_by('-created_at')

    context = {
        'active_groups': active_groups,
        'total_students': total_students,
        'avg_attendace': avg_attendance,
        'pending_today': pending_today,
        'classes': classes,
        'teacher': request.user,
        'profile': request.user.userprofile,
        'now': now(),
        'today_classes': today_classes,
        'total_assignments': total_assignments,
        'today_assignments': today_assignments,
    }

    return render(request, 'teacher_dashboard.html', context)

def edit_assignment(request, id):
    assignment = get_object_or_404(Assignment, id=id, teacher=request.user)

    form = AssignmentForm(instance=assignment)

    if request.method == "POST":
        form = AssignmentForm(request.POST, request.FILES, instance=assignment)
        if form.is_valid():
            form.save()
            return redirect('teacher_dashboard')

    return render(request, 'add_assignment.html', {'form': form})

# DELETE
def delete_assignment(request, id):
    assignment = get_object_or_404(Assignment, id=id, teacher=request.user)
    assignment.delete()
    return redirect('teacher_dashboard')

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

# def teacher_mark_attendance(request, session_id):
#     teacher = request.user

#     groups = ClassGroup.objects.filter(
#         teacher=teacher,
#         is_active=True
#     ).select_related('subject', 'grade')

#     selected_group = None
#     students = []

#     group_id = request.GET.get('group')

#     if group_id:
#         selected_group = get_object_or_404(
#             ClassGroup,
#             id=group_id,
#             teacher=teacher
#         )

#         students = StudentProfile.objects.filter(
#             grade=selected_group.grade
#         ).select_related('user')

#     context = {
#         'groups': groups,
#         'selected_group': selected_group,
#         'students': students,
#         'today': date.today(),
#     }

#     return render(request, 'teacher_mark_attendance.html', context)

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

    # Get form data
    name = request.POST.get('student_name', '').strip()
    student_id = request.POST.get('student_id', '').strip()
    email = request.POST.get('student_email', '').strip().lower()
    password = request.POST.get('student_password', '').strip()

    # ---------------- VALIDATIONS ---------------- #

    # Required fields
    if not name or not student_id or not password:
        messages.error(request, 'Please fill all required fields.')
        return redirect('mark_attendance', group_id=group.id)

    # Student ID: must be exactly 4 digits
    if not re.fullmatch(r'\d{4}', student_id):
        messages.error(request, 'Student ID must be exactly 4 digits.')
        return redirect('mark_attendance', group_id=group.id)

    # Email validation (if provided)
    if email:
        if '@' not in email:
            messages.error(request, 'Invalid email format (must contain @).')
            return redirect('mark_attendance', group_id=group.id)

    # Password validation
    if len(password) < 6:
        messages.error(request, 'Password must be at least 6 characters long.')
        return redirect('mark_attendance', group_id=group.id)

    # ---------------- DUPLICATE CHECKS ---------------- #

    if StudentProfile.objects.filter(student_id=student_id).exists():
        messages.error(request, 'Student ID already exists.')
        return redirect('mark_attendance', group_id=group.id)

    if User.objects.filter(username=student_id).exists():
        messages.error(request, "Username already exists.")
        return redirect('mark_attendance', group_id=group.id)

    if email and User.objects.filter(email=email).exists():
        messages.error(request, "Email already exists.")
        return redirect('mark_attendance', group_id=group.id)

    # ---------------- CREATE USER ---------------- #

    user = User.objects.create_user(
        username=student_id,
        email=email if email else None,
        password=password
    )
    user.first_name = name
    user.save()

    # Create UserProfile
    UserProfile.objects.create(
        user=user,
        role='STUDENT'
    )

    # Create StudentProfile
    student = StudentProfile.objects.create(
        user=user,
        grade=group.grade,
        student_id=student_id,
        class_group=group,
        roll_no=StudentProfile.objects.filter(class_group=group).count() + 1
    )

    # Enrollment
    StudentEnrollment.objects.create(
        student=student,
        class_group=group
    )

    messages.success(request, f'Student "{name}" added successfully.')
    return redirect('mark_attendance', group_id=group.id)

@login_required
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
        'grades': grades,
        'teacher': request.user,
        'profile': request.user.userprofile
    }

    return render(request, 'teacher_reports.html', context)

@login_required
def student_detail_report(request, student_id):
    student = get_object_or_404(StudentProfile, id=student_id)

    attendance_records = Attendance.objects.filter(student=student).order_by('-date')

    total = attendance_records.count()
    present = attendance_records.filter(status='PRESENT').count()
    absent = attendance_records.filter(status='ABSENT').count()
    late = attendance_records.filter(status='LATE').count()

    percentage = 0
    if total > 0:
        percentage = round((present / total) * 100, 2)

    context = {
        'student': student,
        'records': attendance_records,
        'total': total,
        'present': present,
        'absent': absent,
        'late': late,
        'percentage': percentage,
    }

    return render(request, 'student_detail_report.html', context)


@login_required
def student_dashboard(request):

    user = request.user

    # Ensure this account is a student
    if not hasattr(user, 'studentprofile'):
        return redirect('login')

    student = user.studentprofile
    today = now().date()

    # Attendance Logic
    first_day = today.replace(day=1)
    last_day = today.replace(day=monthrange(today.year, today.month)[1])

    monthly_attendance = Attendance.objects.filter(
        student=student,
        date__range=[first_day, last_day]
    )

    total_present = monthly_attendance.filter(status='PRESENT').count()
    total_absent = monthly_attendance.filter(status='ABSENT').count()
    total_classes = monthly_attendance.count()

    attendance_percentage = (
        round((total_present / total_classes) * 100, 1)
        if total_classes > 0 else 0
    )

    # Assignments
    assignments = Assignment.objects.filter(
        class_group=student.class_group,
        due_date__gte = today
    ).order_by('due_date')

    # Submitted assignments
    submitted_ids = AssignmentSubmission.objects.filter(
        student=student
    ).values_list('assignment_id', flat=True)

    # Pending assignments (THIS IS WHAT YOU WANT)
    streak = assignments.exclude(
        id__in=submitted_ids
    ).count()

    assignments = assignments[:3]

    context = {
        'student': student,
        'total_present': total_present,
        'total_absent': total_absent,
        'total_classes': total_classes,
        'attendance_percentage': attendance_percentage,
        'streak': streak, 
        'today_assignments': assignments,
        'submitted_ids': list(submitted_ids),
    }

    return render(request, 'student_dashboard.html', context)

def submit_assignment(request, id):
    assignment = get_object_or_404(Assignment, id=id)
    student = request.user.studentprofile

    if request.method == "POST":
        file = request.FILES.get('file')

        # ✅ VALIDATE FILE TYPE
        if not file:
            messages.error(request, "Please upload a file.")
        elif not file.name.lower().endswith('.pdf'):
            messages.error(request, "Only PDF files are allowed.")
        elif file.size > 5 * 1024 * 1024:  # Optional: limit size to 5MB
            messages.error(request, "File size must be under 5MB.")
        else:
            # Save submission
            AssignmentSubmission.objects.update_or_create(
                assignment=assignment,
                student=student,
                defaults={'submitted_file': file}
            )
            messages.success(request, "Assignment submitted successfully!")
            return redirect('student_dashboard')

    return render(request, 'submit_assignment.html', {
        'assignment': assignment
    })

# def view_submission(request, assignment_id):
#     assignment = get_object_or_404(Assignment, id = assignment_id, teacher = request.user)

#     submissions = AssignmentSubmission.objects.filter(assignment = assignment).select_related('student__user')

#     if request.method == "POST":
#         submission_id = request.POST.get('submission_id')
#         marks = request.POST.get('marks')
#         feedback = request.POST.get('feedback')

#         submission = AssignmentSubmission.objects.get(id = submission_id)
#         submission.marks = marks
#         submission.feedback = feedback
#         submission.save()

#         return redirect('view_submissions', assignment_id = assignment_id)
    
#     return render(request, 'view_submissions.html', {
#         'assignment': assignment,
#         'submissions': submissions
#     })

@login_required
def student_attendance(request):
    # Get current student
    student = get_object_or_404(StudentProfile, user=request.user)

    # Get all groups student is enrolled in
    groups = ClassGroup.objects.filter(studentprofile__user=request.user)

    # Attendance records
    attendance_records = []
    for group in groups:
        total_classes = Attendance.objects.filter(student=student, group=group).count()
        present_count = Attendance.objects.filter(student=student, group=group, status="PRESENT").count()
        absent_count = Attendance.objects.filter(student=student, group=group, status="ABSENT").count()
        late_count = Attendance.objects.filter(student=student, group=group, status="LATE").count()

        percentage = round((present_count / total_classes) * 100, 1) if total_classes > 0 else 0

        if percentage >= 90:
            badge_class = "present"
        elif percentage >= 75:
            badge_class = "warning"
        else:
            badge_class = "late"

        attendance_records.append({
            "group": group,
            "teacher": group.teacher.get_full_name(),
            "total": total_classes,
            "present": present_count,
            "absent": absent_count,
            "late": late_count,
            "percentage": percentage,
            "badge_class": badge_class
        })

    # Stats overview
    total_classes = sum([r["total"] for r in attendance_records])
    total_present = sum([r["present"] for r in attendance_records])
    total_absent = sum([r["absent"] for r in attendance_records])
    total_late = sum([r["late"] for r in attendance_records])
    overall_percentage = round((total_present / total_classes) * 100, 1) if total_classes > 0 else 0

    context = {
        "student": student,
        "attendance_records": attendance_records,
        "stats": {
            "overall_percentage": overall_percentage,
            "classes_attended": total_present,
            "total_absences": total_absent,
            "late_arrivals": total_late,
        }
    }
    return render(request, "student-attendance.html", context)

@login_required
def student_mark_attendance(request):

    # Get logged in student
    student = get_object_or_404(StudentProfile, user=request.user)

    today = date.today()

    # Attendance records for today
    attendance_today = Attendance.objects.filter(
        student=student,
        date=today
    ).select_related("group", "group__subject", "group__teacher")

    # Groups the student belongs to
    groups = ClassGroup.objects.filter(
        studentprofile__user=request.user
    ).distinct()

    classes_today = groups.count()
    attended = attendance_today.filter(status="PRESENT").count()
    remaining = classes_today - attended

    context = {
        "student": student,
        "attendance_today": attendance_today,
        "classes_today": classes_today,
        "attended": attended,
        "remaining": remaining
    }

    return render(request, "student_mark_attendance.html", context)

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

@login_required
def student_class_shedule(request):
    user = request.user

    # Check if student profile exists
    if not hasattr(user, 'studentprofile'):
        return redirect('login')

    student = user.studentprofile

    # Safety: check class group assigned
    if not student.class_group:
        return render(request, 'student_class_schedule.html', {
            'assignments': [],
            'submitted_ids': [],
            'error': "No class group assigned to you."
        })

    # All assignments for the student's class
    assignments = Assignment.objects.filter(
        class_group_id=student.class_group_id,
        class_group__is_active=True
    ).select_related('subject', 'teacher').order_by('-created_at')

    # Submitted assignments
    submitted_ids = AssignmentSubmission.objects.filter(
        student=student
    ).values_list('assignment_id', flat=True)

    context = {
        'assignments': assignments,
        'submitted_ids': list(submitted_ids),
        'today': now().date()  # Pass today to template
    }

    return render(request, 'student_class_schedule.html', context)

def add_assignment(request):
    form = AssignmentForm()

    # filter groups for logged-in teacher
    form.fields['class_group'].queryset = ClassGroup.objects.filter(
        teacher=request.user
    )

    if request.method == "POST":
        form = AssignmentForm(request.POST, request.FILES)
        form.fields['class_group'].queryset = ClassGroup.objects.filter(
            teacher=request.user
        )
        form.fields['subject'].queryset = Subject.objects.all()

        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.teacher = request.user
            assignment.save()
            return redirect('teacher_dashboard')

    return render(request, 'add_assignment.html', {'form': form})

@login_required
def view_teacher_assignments(request):
    teacher = request.user

    # Get all assignments created by this teacher
    assignments = Assignment.objects.filter(teacher=teacher).order_by('-created_at')  # Latest first

    # Optionally, fetch number of submissions for each assignment
    assignments_with_submissions = []
    for assignment in assignments:
        submissions_count = AssignmentSubmission.objects.filter(assignment=assignment).count()
        assignments_with_submissions.append({
            'assignment': assignment,
            'submissions_count': submissions_count
        })

    context = {
        'assignments_with_submissions': assignments_with_submissions,
    }

    return render(request, 'view_teacher_assignments.html', context)

def view_submissions_list(request, assignment_id):
    # Get assignment
    assignment = get_object_or_404(Assignment, id=assignment_id)

    # Fetch all submissions for this assignment
    submissions = AssignmentSubmission.objects.filter(
        assignment=assignment
    ).select_related('student', 'student__user').order_by('-submitted_at')  # latest first

    context = {
        'assignment': assignment,
        'submissions': submissions
    }
    return render(request, 'teacher_submissions_list.html', context)