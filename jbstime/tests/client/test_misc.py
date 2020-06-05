from datetime import date
from decimal import Decimal
from unittest.mock import patch, PropertyMock

from jbstime.api import PTO, TimesheetItem
from jbstime.error import Error


def test_create(run):
  result = run('create', '5/24')
  assert result.exit_code == 0
  assert result.output == 'Created timesheet for May 24, 2020\n'

  result = run('create', '5/10')
  assert result.exit_code == Error.TIMESHEET_EXISTS
  assert result.output == 'A timesheet already exists for May 10, 2020\n'


def test_holidays(run):
  result = run('holidays')
  assert result.exit_code == 0
  assert result.output.startswith('May 25, 2020: Memorial Day')


@patch('jbstime.api.pto')
@patch('jbstime.api.Timesheet.items', new_callable=PropertyMock)
def test_pto(mock_items, mock_pto, run):
    mock_pto.return_value = PTO(
      balance=Decimal('1.0'),
      cap=Decimal('10.0'),
      earned=Decimal('100.0'),
      used=Decimal('90.5'),
      accrual=110
    )

    mock_pto.return_value = PTO(1, 1, 1, 1, 1)
    result = run('pto')
    assert result.exit_code == 0
    assert result.output.startswith('You have 1 hour remaining')

    mock_pto.return_value = PTO(
      balance=Decimal('9.5'),
      cap=Decimal('10.00'),
      earned=Decimal('100.0'),
      used=Decimal('90.5'),
      accrual=110
    )

    result = run('pto')
    assert result.exit_code == 0
    assert result.output == '''You have 9.5 hours remaining
You have earned 100.0 hours and used 90.5 hours
You earn a day for every 110 hours
You are capped at 10.00 hours
'''

    mock_items.return_value = set([
      TimesheetItem(1, Decimal('4.0'), date(2020, 5, 18), 'Test Project', 'Test'),
      TimesheetItem(2, Decimal('7.0'), date(2020, 5, 19), 'Test Project', 'Test'),
      TimesheetItem(3, Decimal('1.0'), date(2020, 5, 20), 'Test Project', 'Test'),
      TimesheetItem(4, Decimal('1.0'), date(2020, 5, 20), 'Test Project', 'Test 2'),
      TimesheetItem(5, Decimal('8.0'), date(2020, 5, 22), 'Test Project', 'Test'),
    ])
    result = run('pto')
    assert result.exit_code == 0
    assert 'additional hours exceeds your PTO cap\nCurrent timesheet puts you at 11.03.' in result.output

    with patch('jbstime.api.Timesheet.locked', new_callable=PropertyMock, return_value=True):
      result = run('pto')
      assert result.exit_code == 0
      assert 'additional hours exceeds your PTO cap' not in result.output

    mock_items.return_value = set([
      TimesheetItem(1, Decimal('4.0'), date(2020, 5, 18), 'Test Project', 'Test'),
      TimesheetItem(2, Decimal('7.0'), date(2020, 5, 19), 'Test Project', 'Test'),
      TimesheetItem(3, Decimal('1.0'), date(2020, 5, 20), 'Test Project', 'Test'),
      TimesheetItem(4, Decimal('1.0'), date(2020, 5, 20), 'Test Project', 'Test 2'),
      TimesheetItem(5, Decimal('8.0'), date(2020, 5, 22), 'JBS - PTO', 'Test'),
    ])
    result = run('pto')
    assert result.exit_code == 0
    assert 'additional hours exceeds your PTO cap' not in result.output


def test_login(run, no_config):
  result = run('--user', 'user', '--pass', 'foo', 'holidays')
  assert result.exit_code == 0
  assert result.output.startswith('May 25, 2020: Memorial Day')

  result = run('--user', 'baduser', '--pass', 'foo', 'holidays')
  assert result.exit_code == Error.LOGIN_FAILED
  assert result.output == 'Login failed. Check your username and password.\n'

  result = run('holidays', '--help')
  assert result.exit_code == 0
  assert result.output.startswith('Usage: cli holidays [OPTIONS]\n')


def test_projects(run):
  result = run('projects')
  assert result.exit_code == 0
  assert result.output == 'JBS - Paid Holiday\nJBS - PTO\nJBS - PTO Exchange\nJBS Non-Billable\nTest Project\n'

  result = run('projects', '--all')
  assert result.exit_code == 0
  assert 'JBS - Jury Duty' in result.output

  result = run('projects', 'jury')
  assert result.exit_code == 0
  assert result.output == ''

  result = run('projects', 'jury', '--all')
  assert result.exit_code == 0
  assert 'JBS - Jury Duty' in result.output
  assert 'Paid Holiday' not in result.output


def test_timesheet(run):
  result = run('timesheet')
  assert result.exit_code == 0
  assert result.output.startswith('\nTimesheet for May 24, 2020 (24.00 hours, unsubmitted)')

  result = run('timesheet', '5/24/2020')
  assert result.exit_code == 0
  assert result.output.startswith('\nTimesheet for May 24, 2020 (24.00 hours, unsubmitted)')

  with patch('jbstime.api.Timesheet.items', new_callable=PropertyMock) as items_mock:
    items_mock.return_value = {}
    result = run('timesheet', '5/24/2020')
    assert result.exit_code == 0
    assert result.output == 'No hours added to the timesheet for May 24, 2020\n'


def test_timesheets(run):
  result = run('timesheets')
  assert result.exit_code == 0
  assert result.output.startswith('May 24, 2020   24.00  (unsubmitted)')
  assert '\nMay 10, 2020   48.00\n' in result.output
  assert len(result.output.split('\n')) == 5

  result = run('timesheets', '--limit', '10')
  assert result.exit_code == 0
  assert len(result.output.split('\n')) == 10

  result = run('timesheets', '--limit', 'all')
  assert result.exit_code == 0
  assert len(result.output.split('\n')) == 21

  result = run('timesheets', '--limit', 'foo')
  assert result.exit_code == Error.INVALID_ARGUMENT


@patch('jbstime.api.Timesheet.hours', new_callable=PropertyMock)
@patch('jbstime.api.Timesheet.submit')
def test_submit(mock_submit, mock_hours, run):
  mock_hours.return_value = 40.0
  result = run('submit', '05/24/2020', input='y')
  assert result.exit_code == 0
  assert result.output == 'Submitted timesheet for May 24, 2020\n'
  mock_submit.assert_called_once()

  mock_hours.return_value = 38.0
  result = run('submit', '05/24/2020', input='n')
  assert result.exit_code == 0
  assert result.output == 'There are only 38.0 hours logged. Submit anyway? [y/N]: n\n'
  mock_submit.assert_called_once()

  mock_hours.return_value = 1.0
  result = run('submit', '05/24/2020', input='n')
  assert result.exit_code == 0
  assert result.output == 'There is only 1.0 hour logged. Submit anyway? [y/N]: n\n'
  mock_submit.assert_called_once()

  mock_hours.return_value = 0.0
  result = run('submit', '05/24/2020', input='n')
  assert result.exit_code == 0
  assert result.output == 'There is no time logged. Submit anyway? [y/N]: n\n'
  mock_submit.assert_called_once()

  result = run('submit', '5/17/2020')
  assert result.exit_code == Error.TIMESHEET_SUBMITTED


@patch('jbstime.api.Timesheet.delete_item')
def test_delete(mock_delete, run):
  result = run('delete', '5/24/2020', 'Test Project', '--all', input='n')
  assert result.exit_code == 0
  assert result.output == '5 items to delete\nAre you sure? [y/N]: n\n'
  mock_delete.assert_not_called()

  result = run('delete', '5/24/2020', 'Test Project', '--all', input='y')
  assert result.exit_code == 0
  assert result.output == '5 items to delete\nAre you sure? [y/N]: y\n'
  assert mock_delete.call_count == 5

  result = run('delete', '5/24/2020', 'Test Project')
  assert result.exit_code == 0
  assert result.output == 'No matching items\n'

  result = run('delete', '5/24/2020', 'Test Project', 'Missing Description', '--all')
  assert result.exit_code == 0
  assert result.output == 'No matching items\n'
