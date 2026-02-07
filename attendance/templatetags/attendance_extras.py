from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.simple_tag
def get_attendance(records_dict, student_id, date):
    return records_dict.get(student_id, "")  # only stored records

@register.simple_tag
def get_status_icon(records_dict, student_id, date):
    status = get_attendance(records_dict, student_id, date)
    icons = {"PRESENT": "✓", "ABSENT": "✗", "LATE": "L", "HOLIDAY": "H", "": ""}
    return icons.get(status, "")
