from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone
from datetime import timedelta

# Create your models here.
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('TEACHER', 'Teacher'),
        ('STUDENT', 'Student')
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=10, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)

    # Emergency contact
    emergency_name = models.CharField(max_length=100, blank=True)
    emergency_relation = models.CharField(max_length=50, blank=True)
    emergency_phone = models.CharField(max_length=15, blank=True)
    emergency_email = models.EmailField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
class Grade(models.Model):
    name = models.CharField(max_length=20, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name

class ClassGroup(models.Model):
    name = models.CharField(max_length=100)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    semester = models.CharField(max_length=20, blank=True, default='None')
    created_at = models.DateTimeField(auto_now_add=True)    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='studentprofile', null=True, blank=True)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    roll_no = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username

class StudentEnrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'class_group')


class AttendanceSession(models.Model):
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name='sessions')
    date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('class_group', 'date')
    
    def __str__(self):
        return f"{self.class_group} - {self.date}"

class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late')
    ]
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ('session', 'student')

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('HOLIDAY', 'Holiday'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)

    date = models.DateField()

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES
    )

    is_locked = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'group', 'date')


class QRCode(models.Model):
    session = models.OneToOneField(AttendanceSession, on_delete=models.CASCADE)
    code = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

# class FaceEncoding(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     encoding = models.BinaryField()


# models.py

class Assignment(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name='assignments')

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    title = models.CharField(max_length=255)
    description = models.TextField()

    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    file = models.FileField(upload_to='assignments/', null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.class_group.name}"

class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)

    submitted_file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)

    marks = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = ('assignment', 'student')

class AttendanceQR(models.Model):
    group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    date = models.DateField()
    qr_code_file = models.ImageField(upload_to='qr_codes/')
    expires_at = models.DateTimeField()
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['group', 'date'], name='unique_qr_per_day')
        ]

    def is_valid(self):
        return timezone.now() < self.expires_at