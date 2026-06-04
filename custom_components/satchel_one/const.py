"""Constants for the Satchel One integration."""

DOMAIN = "satchel_one"

# Default polling intervals (seconds)
DEFAULT_HOMEWORK_UPDATE_INTERVAL = 30 * 60  # 30 minutes
DEFAULT_BEHAVIOUR_UPDATE_INTERVAL = 15 * 60  # 15 minutes
MIN_UPDATE_INTERVAL = 5 * 60  # 5 minutes (hard floor)

# Event names
EVENT_HOMEWORK_NEW = "satchel_one_new_homework"
EVENT_HOMEWORK_OVERDUE = "satchel_one_homework_overdue"
EVENT_BEHAVIOUR_CREDIT = "satchel_one_credit"
EVENT_BEHAVIOUR_DEMERIT = "satchel_one_demerit"
EVENT_DETENTION_NEW = "satchel_one_detention"

# TODO: attendance — endpoint not yet captured from live traffic.
# When captured, add ENDPOINT_ATTENDANCE to api/const_api.py,
# an AttendanceSensor, and EVENT_ATTENDANCE_* events here.

# Entity attributes
ATTR_CHILD_ID = "child_id"
ATTR_CHILD_NAME = "child_name"
ATTR_LINKED_PERSON = "linked_person"
