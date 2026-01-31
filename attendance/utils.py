from django.shortcuts import redirect

def redirect_user_by_role(user):
    role = user.userprofile.role

    if role == 'TEACHER':
        return redirect('teacher_dashboard')
    elif role == 'STUDENT':
        return redirect('student_dashboard')
    else:
        return redirect('signin')