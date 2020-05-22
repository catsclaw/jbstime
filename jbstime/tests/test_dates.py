from datetime import date, datetime

import pytest

from jbstime.dates import date_fmt, date_fmt_pad_day, date_from_user_date, find_sunday
from jbstime.error import Error


def test_date_fmt():
  d = date(2000, 1, 1)
  assert date_fmt(d) == 'Jan 1, 2000'
  assert date_fmt_pad_day(d) == 'Jan  1, 2000'


def test_date_from_user():
  assert date(2000, 1, 1) == date_from_user_date('jan 1, 2000')

  today = datetime.now().date()
  assert today == date_from_user_date('today') == date_from_user_date('current')

  with pytest.raises(SystemExit) as e:
    date_from_user_date('blah')

  assert e.value.code == Error.UNPARSABLE_DATE


def test_sunday():
  sunday = date(2000, 1, 2)
  assert find_sunday(date(2000, 1, 1)) == sunday
  assert find_sunday(date(1999, 12, 30)) == sunday
  assert find_sunday(sunday) == sunday
