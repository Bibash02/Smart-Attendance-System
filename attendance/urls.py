from django.urls import path
from .views import *

urlpatterns = [
    path('', auth, name='signin'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout, name='logout'),
    path('forgot-password', forgot_password, name='forgot_password'),

    path('teacher/dashboard', teacher_dashboard, name='teacher_dashboard'),
    path('teacher/mark', mark_attendance, name='mark_attendance'),
    path('teacher/groups', groups, name='groups'),
    path('teacher/attendance', qr_attendance, name='qr-attendance'),
    path('teacher/reports', reports, name='reports'),

    path('student/dashboard', student_dashboard, name='student_dashboard'),
]