from enum import IntEnum


class Error(IntEnum):
  INVALID_ARGUMENT = 1
  TIMESHEET_MISSING = 2
  UNPARSABLE_DATE = 3
  TIMESHEET_EXISTS = 4
