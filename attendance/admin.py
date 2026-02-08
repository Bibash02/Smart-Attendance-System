from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'role', 'phone', 'profile_image']

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'is_active', 'created_at']
    list_filter = ['name',]
    search_fields = ['name',]

@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'subject', 'teacher', 'grade', 'semester', 'created_at', 'is_active']
    list_filter = ['grade', 'subject']
    search_fields = ['subject', 'grade']

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'student_id', 'class_group', 'roll_no', 'is_active']
    list_filter = ['student_id', 'roll_no']
    search_fields = ['user', 'roll_no']

@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'student', 'class_group', 'joined_at']
    list_filter = ['class_group', 'student']
    search_fields = ['student']

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'class_group', 'date', 'created_by', 'created_at']
    list_filter = ['class_group', 'date']
    search_fields = ['created_by']

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'student', 'status']
    list_filter = ['session', 'status']
    search_fields = ['student']

@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'code', 'is_active']
    list_filter = ['session', 'code']
    search_fields = ['is_active']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'student', 'group', 'date', 'status', 'is_locked', 'created_at']