from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'role', 'phone', 'profile_image']

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'is_active', 'created_at']
