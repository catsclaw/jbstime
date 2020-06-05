from unittest.mock import patch

import pytest

from jbstime.api import _clear, pto, Timesheet
from jbstime.error import Error


@patch('jbstime.api.Timesheet.list')
def test_latest(mock_list):
  mock_list.return_value = {}
  with pytest.raises(SystemExit) as e:
    Timesheet.latest()

  assert e.value.code == Error.TIMESHEET_MISSING


def test_from_user_date():
  with pytest.raises(SystemExit) as e:
    Timesheet.from_user_date('5/16/2030')

  assert e.value.code == Error.TIMESHEET_MISSING

  with patch('jbstime.api.Timesheet.list') as mock_list:
    mock_list.return_value = {}
    with pytest.raises(SystemExit) as e:
      Timesheet.from_user_date('5/16/2020')

    assert e.value.code == Error.TIMESHEET_MISSING


def test_delete():
  Timesheet.latest().delete_item('27358')


def test_submit():
  Timesheet.latest().submit()


def test_pto():
  _clear()
  pto()


def test_hash():
  hash(Timesheet.latest())
