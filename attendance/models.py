from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('TEACHER', 'Teacher'),
        ('STUDENT', 'Student')
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=10, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
class Grade(models.Model):
    name = models.CharField(max_length=20, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ClassGroup(models.Model):
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    semester = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    roll_no = models.CharField(max_length=10)
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
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('class_group', 'date')

class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late')
    ]
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ('session', 'student')

class QRCode(models.Model):
    session = models.OneToOneField(AttendanceSession, on_delete=models.CASCADE)
    code = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

# class FaceEncoding(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     encoding = models.BinaryField()

    