from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.simple_tag
def get_attendance(records, student_id, date):
    for r in records:
        if r.student_id == student_id and r.date == date:
            return r.status
    return ''

@register.simple_tag
def get_status_icon(records, student_id, date):
    status = get_attendance(records, student_id, date)
    return {
        'PRESENT': '✓',
        'ABSENT': '✗',
        'LATE': 'L',
        'HOLIDAY': 'H',
        '': '○'
    }.get(status, '○')