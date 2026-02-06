from django.urls import path
from .views import *

urlpatterns = [
    path('', auth, name='signin'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout, name='logout'),
    path('forgot-password', forgot_password, name='forgot_password'),

    path('teacher/dashboard', teacher_dashboard, name='teacher_dashboard'),
    path('teacher/mark', teacher_mark_attendance, name='teacher_mark_attendance'),
    path('teacher/groups', teacher_groups, name='teacher_groups'),
    path('teacher/attendance', teacher_qr_attendance, name='teacher_qr-attendance'),
    path('teacher/reports', teacher_reports, name='teacher_reports'),

    path('teacher/mark-attendance/<int:group_id>/', mark_attendance, name='mark_attendance'),
    path('teacher/group/list', group_list, name='group_list'),
    path('teacher/add-student/<int:group_id>/', add_student_to_group, name='add_student'),
    path('teacher/report/<int:group_id>/', attendance_report, name='report'),

    path('student/dashboard', student_dashboard, name='student_dashboard'),
    path('student/attendance', student_attendance, name='student_attendance'),
    path('student/schedule', student_class_schedule, name='class_schedule'),
    path('student/attendance', student_mark_attendance, name='mark_attendance'),
    path('student/profile', student_profile, name='student_profile'),
    path('student/profile/edit', student_profile_edit, name='student_profile_edit'),
]