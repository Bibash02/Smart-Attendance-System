from django.shortcuts import render

# Create your views here.
def teacher_dashboard(request):
    return render(request, 'teacher_dashboard.html')

def mark_attendance(request):
    return render(request, 'mark_attendance.html')

def groups(request):
    return render(request, 'groups.html')

def qr_attendance(request):
    return render(request, 'qr-attendance.html')

def reports(request):
    return render(request, 'reports.html')