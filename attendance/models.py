from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Profile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('TEACHER', 'Teacher'),
        ('STUDENT', 'Student')
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=10, blank=True)
    photo = models.ImageField(upload_to='profiles/', null=True, blank=True)

class Group(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

class GroupMember(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    method = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

class AttendanceSession(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    taken_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    start_time = models.TimeField(auto_now_add=True)

class QRCode(models.Model):
    session = models.OneToOneField(AttendanceSession, on_delete=models.CASCADE)
    code = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

# class FaceEncoding(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     encoding = models.BinaryField()