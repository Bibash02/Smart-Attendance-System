from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.simple_tag
def get_attendance(records, student_id, date):
    return records.get((student_id, date), 'PRESENT')

@register.simple_tag
def get_status_icon(records, student_id, date):
    status = records.get((student_id, date), 'PRESENT')
    return '✓' if status == 'PRESENT' else '✗'