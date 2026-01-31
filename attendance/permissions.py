
def is_teacher(user):
    return hasattr(user, 'userprofile') and user.userprofile.role == 'TEACHER'

def is_student(user):
    return hasattr(user, 'userprofile') and user.userprofile.role == 'STUDENT'