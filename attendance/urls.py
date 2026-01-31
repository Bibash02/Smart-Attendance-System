from django.urls import path
from .views import *

urlpatterns = [
    path('auth/', auth, name='auth'),
    path('login', login_view, name='login'),
    path('register', register_view, name='register'),

    path('teacher/dashboard', teacher_dashboard, name='teacher_dashboard'),
    path('teacher/mark', mark_attendance, name='mark_attendance'),
    path('teacher/groups', groups, name='groups'),
    path('teacher/attendance', qr_attendance, name='qr-attendance'),
    path('teacher/reports', reports, name='reports')
]