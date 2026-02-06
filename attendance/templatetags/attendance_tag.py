from django import template

register = template.Library()

@register.filter
def get_attendance(records, student_id):
    """
    Get attendance records for a specific student
    Usage: {{ records|get_attendance:student.id }}
    """
    if isinstance(records, dict):
        return records.get(student_id, {})
    return {}

@register.filter
def get_date(student_records, date):
    """
    Get status for a specific date
    Usage: {{ student_records|get_date:date }}
    """
    if isinstance(student_records, dict):
        date_str = date.strftime('%Y-%m-%d')
        return student_records.get(date_str, 'PRESENT')
    return 'PRESENT'

@register.filter
def get_status_icon(status):
    """
    Get icon for attendance status
    """
    icons = {
        'PRESENT': '✓',
        'ABSENT': '✗',
        'LATE': 'L'
    }
    return icons.get(status, '✓')