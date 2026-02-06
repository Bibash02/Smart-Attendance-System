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
from datetime import date, datetime, timedelta
from calendar import monthrange
from django.db import transaction


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

# def mark_attendance(request, group_id):
#     group = get_object_or_404(
#         ClassGroup,
#         id=group_id,
#         teacher=request.user
#     )

#     selected_date = request.GET.get('date') or date.today()

#     students = StudentProfile.objects.filter(
#         grade=group.grade
#     ).select_related('user')

#     session, created = AttendanceSession.objects.get_or_create(
#         class_group=group,
#         date=selected_date,
#         defaults={'created_by': request.user}
#     )

#     if request.method == 'POST':
#         for student in students:
#             status = request.POST.get(f'status_{student.id}', 'PRESENT')

#             AttendanceRecord.objects.update_or_create(
#                 session=session,
#                 student=student,
#                 defaults={'status': status}
#             )

#         return redirect('mark_attendance', group_id=group.id)

#     existing_records = {
#         r.student_id: r.status
#         for r in session.records.all()
#     }

#     return render(request, 'mark_attendance.html', {
#         'group': group,
#         'students': students,
#         'session': session,
#         'records': existing_records,
#         'selected_date': selected_date,
#     })

def mark_attendance(request, group_id):
    group = get_object_or_404(ClassGroup, id=group_id)
    
    # Get selected month or default to current month
    selected_month = request.GET.get('month') or request.POST.get('month')
    if selected_month:
        try:
            year, month = map(int, selected_month.split('-'))
        except:
            year, month = datetime.now().year, datetime.now().month
    else:
        year, month = datetime.now().year, datetime.now().month
    
    # Handle form submission
    if request.method == 'POST':
        return save_attendance(request, group, year, month)
    
    # Get all students in this class group
    students = StudentProfile.objects.filter(
        class_group=group,
        is_active=True
    ).select_related('user', 'grade').order_by('roll_no')
    
    # Generate all dates for the selected month
    num_days = monthrange(year, month)[1]
    dates = [datetime(year, month, day).date() for day in range(1, num_days + 1)]
    
    # Get existing attendance sessions and records for this month
    start_date = datetime(year, month, 1).date()
    end_date = datetime(year, month, num_days).date()
    
    sessions = AttendanceSession.objects.filter(
        class_group=group,
        date__range=[start_date, end_date]
    ).prefetch_related('records')
    
    # Create a dictionary for easy lookup: {student_id: {date: status}}
    records = {}
    for session in sessions:
        for record in session.records.all():
            if record.student.id not in records:
                records[record.student.id] = {}
            records[record.student.id][session.date.strftime('%Y-%m-%d')] = record.status
    
    context = {
        'group': group,
        'students': students,
        'dates': dates,
        'records': records,
        'selected_month': f"{year}-{month:02d}",
    }
    
    return render(request, 'mark_attendance.html', context)

def save_attendance(request, group, year, month):
    """Save attendance records from the form submission"""
    try:
        saved_count = 0
        updated_count = 0
        
        # Dictionary to group records by date
        date_records = {}
        
        # Get all POST data and organize by date
        for key, value in request.POST.items():
            if key.startswith('attendance_'):
                # Parse the key: attendance_{student_id}_{date}
                parts = key.split('_')
                if len(parts) == 3:
                    student_id = parts[1]
                    date_str = parts[2]
                    status = value
                    
                    if date_str not in date_records:
                        date_records[date_str] = []
                    
                    date_records[date_str].append({
                        'student_id': student_id,
                        'status': status
                    })
        
        # Process each date
        for date_str, student_data in date_records.items():
            try:
                attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Get or create attendance session for this date
                session, session_created = AttendanceSession.objects.get_or_create(
                    class_group=group,
                    date=attendance_date,
                    defaults={
                        'marked_by': request.user
                    }
                )
                
                # Update or create records for each student
                for data in student_data:
                    try:
                        student = StudentProfile.objects.get(id=data['student_id'])
                        
                        record, created = AttendanceRecord.objects.update_or_create(
                            session=session,
                            student=student,
                            defaults={
                                'status': data['status']
                            }
                        )
                        
                        if created:
                            saved_count += 1
                        else:
                            updated_count += 1
                            
                    except StudentProfile.DoesNotExist:
                        continue
                
            except ValueError:
                continue
        
        messages.success(
            request, 
            f'Successfully saved attendance! New: {saved_count}, Updated: {updated_count}'
        )
        
    except Exception as e:
        messages.error(request, f'Error saving attendance: {str(e)}')
    
    # Redirect back to the same page with the same month
    return redirect(f'/attendance/mark/{group.id}/?month={year}-{month:02d}')

@login_required
def add_student_to_group(request, group_id):
    """AJAX endpoint to add a new student to a group"""
    if request.method == 'POST':
        try:
            group = get_object_or_404(ClassGroup, id=group_id)
            
            # Get form data
            student_name = request.POST.get('student_name')
            student_id = request.POST.get('student_id')
            student_email = request.POST.get('student_email', '')
            roll_no = request.POST.get('roll_no', '')
            
            # Check if student_id already exists
            if StudentProfile.objects.filter(student_id=student_id).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Student ID already exists!'
                }, status=400)
            
            # Split name into first and last name
            name_parts = student_name.strip().split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Create username from student_id
            username = student_id
            
            # Check if username exists
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Username already exists!'
                }, status=400)
            
            # Create user
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=student_email,
                password=student_id  # Default password is student_id
            )
            
            # Create student profile
            student = StudentProfile.objects.create(
                user=user,
                student_id=student_id,
                class_group=group,
                grade=group.grade,
                roll_no=roll_no if roll_no else str(StudentProfile.objects.filter(class_group=group).count() + 1)
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Student added successfully!',
                'student': {
                    'id': student.id,
                    'name': student.user.get_full_name(),
                    'student_id': student.student_id,
                    'roll_no': student.roll_no
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

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
    
    return render(request, 'attendance/report.html', context)

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
    
    return render(request, 'attendance/group_list.html', context)

def teacher_groups(request):
    user = request.user
    profile = user.userprofile
    grades = Grade.objects.filter(is_active = True)

    groups = ClassGroup.objects.filter(
        teacher = request.user,
        is_active = True
    ).select_related('subject', 'grade')

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