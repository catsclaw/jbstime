from datetime import date
from unittest.mock import call, patch, PropertyMock

from jbstime import req
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


def test_pto(run):
  result = run('pto')
  assert result.exit_code == 0
  assert result.output == '''You have 100.0 hours remaining
You have earned 200.0 hours and used 100.0 hours
You earn a day for every 150 hours
You are capped at 160 hours
'''

  with patch('jbstime.api.pto') as mock_pto:
    mock_pto.return_value = PTO(1, 1, 1, 1, 1)
    result = run('pto')
    assert result.exit_code == 0
    assert result.output.startswith('You have 1 hour remaining')


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
  assert result.output.startswith('\nTimesheet for May 24, 2020 (24.0 hours, unsubmitted)')

  result = run('timesheet', '5/24/2020')
  assert result.exit_code == 0
  assert result.output.startswith('\nTimesheet for May 24, 2020 (24.0 hours, unsubmitted)')

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


def test_add(run):
  result = run('add', '5/18/2020', 'Test Project', '8', 'Testing')
  assert result.exit_code == 0
  assert result.output == ''

  result = run('add', '5/18/2020', 'Test Project', 'foo', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Invalid hours: foo\n'

  result = run('add', '5/18/2020', 'Test Project', '100', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Too many hours: 100.0\n'

  result = run('add', '5/18/2020', 'Test Project', '--', '-5', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Hours cannot be negative: -5.0\n'

  result = run('add', '5/18/2020', 'Test Project', '0', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Hours cannot be 0\n'

  result = run('add', '5/18/2020', 'Test Project', '8', '  ')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'No description provided\n'

  result = run('add', '5/18/2020', 'Missing Project', '8', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Invalid project: Missing Project\n'


@patch('jbstime.api.Timesheet.add_item')
@patch('jbstime.api.list_holidays')
def test_addall(mock_holidays, mock_add, run):
  mock_holidays.return_value = {}
  result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing')
  assert result.exit_code == 0
  assert result.output == ''
  assert mock_add.call_count == 5
  mock_add.assert_has_calls([
    call(date(2020, 5, 18), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 19), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 20), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 21), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 22), 'Test Project', '8', 'Testing', fill=True, merge=True),
  ], any_order=True)

  mock_holidays.return_value = {
    date(2020, 5, 18): 'Holiday A',
  }
  mock_add.reset_mock()
  result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing', input='y')
  assert result.exit_code == 0
  assert result.output.startswith('May 18, 2020 is Holiday A\n')
  assert 'Set holidays to time off?' in result.output
  assert mock_add.call_count == 5
  mock_add.assert_has_calls([
    call(date(2020, 5, 18), 'JBS - Paid Holiday', 8, 'Holiday A', fill=True, merge=True),
    call(date(2020, 5, 19), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 20), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 21), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 22), 'Test Project', '8', 'Testing', fill=True, merge=True),
  ], any_order=True)

  mock_holidays.return_value = {
    date(2020, 5, 18): 'Holiday A',
    date(2020, 5, 19): 'Holiday B',
  }
  mock_add.reset_mock()
  result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing', input='y')
  assert result.exit_code == 0
  assert result.output.startswith('May 18, 2020 is Holiday A and May 19, 2020 is Holiday B\n')
  assert 'Set holidays to time off?' in result.output
  assert mock_add.call_count == 5
  mock_add.assert_has_calls([
    call(date(2020, 5, 18), 'JBS - Paid Holiday', 8, 'Holiday A', fill=True, merge=True),
    call(date(2020, 5, 19), 'JBS - Paid Holiday', 8, 'Holiday B', fill=True, merge=True),
    call(date(2020, 5, 20), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 21), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 22), 'Test Project', '8', 'Testing', fill=True, merge=True),
  ], any_order=True)

  mock_holidays.return_value = {
    date(2020, 5, 18): 'Holiday A',
    date(2020, 5, 19): 'Holiday B',
    date(2020, 5, 20): 'Holiday C',
  }
  mock_add.reset_mock()
  result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing', input='n')
  assert result.exit_code == 0
  assert 'May 18, 2020 is Holiday A, May 19, 2020 is Holiday B, and May 20, 2020 is Holiday C\n' in result.output
  assert 'Set holidays to time off?' in result.output
  assert mock_add.call_count == 5
  mock_add.assert_has_calls([
    call(date(2020, 5, 18), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 19), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 20), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 21), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 22), 'Test Project', '8', 'Testing', fill=True, merge=True),
  ], any_order=True)


@patch('jbstime.api.list_holidays')
@patch('jbstime.api.Timesheet.items', new_callable=PropertyMock)
def test_addall_fill(mock_items, mock_holidays, run):
  mock_items.return_value = set([
    TimesheetItem(1, 4.0, date(2020, 5, 18), 'Test Project', 'Test'),
    TimesheetItem(2, 7.0, date(2020, 5, 19), 'Test Project', 'Test'),
    TimesheetItem(3, 1.0, date(2020, 5, 20), 'Test Project', 'Test'),
    TimesheetItem(4, 1.0, date(2020, 5, 20), 'Test Project', 'Test 2'),
    TimesheetItem(5, 8.0, date(2020, 5, 22), 'Test Project', 'Test'),
  ])
  mock_holidays.return_value = {
    date(2020, 5, 18): 'Holiday A',
  }

  with patch('jbstime.req.post', wraps=req.post) as post_func:
    result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing', input='y')
    assert result.exit_code == 0

    def look_for_hours(date, project, hours):  # pragma: no cover
      for c in post_func.call_args_list:
        data = c[1]['data']

        if all([data.get('log_date') == date, data.get('project') == project, data.get('hours_worked') == hours]):
          return True

      return False

    assert look_for_hours('05/18/2020', '8', 4.0)
    assert look_for_hours('05/19/2020', '10000', 1.0)
    assert look_for_hours('05/20/2020', '10000', 6.0)
    assert look_for_hours('05/21/2020', '10000', 8.0)

    post_func.reset_mock()
    result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing', '--no-fill', input='y')
    assert result.exit_code == 0

    assert look_for_hours('05/18/2020', '8', 8.0)
    assert look_for_hours('05/19/2020', '10000', 8.0)
    assert look_for_hours('05/20/2020', '10000', 8.0)
    assert look_for_hours('05/21/2020', '10000', 8.0)
    assert look_for_hours('05/22/2020', '10000', 8.0)


@patch('jbstime.api.Timesheet.items', new_callable=PropertyMock)
def test_addall_merge(mock_items, run):
  mock_items.return_value = set([
    TimesheetItem(1, 4.0, date(2020, 5, 18), 'Test Project', 'Test Merge'),
    TimesheetItem(2, 7.0, date(2020, 5, 19), 'Test Project', 'Test'),
    TimesheetItem(3, 1.0, date(2020, 5, 20), 'Test Project', 'Test Merge'),
    TimesheetItem(4, 1.0, date(2020, 5, 20), 'Test Project', 'Test 2'),
    TimesheetItem(5, 8.0, date(2020, 5, 22), 'Test Project', 'Test'),
  ])

  with patch('jbstime.req.post', wraps=req.post) as post_func:
    result = run('addall', '5/18/2020', 'Test Project', '2', 'Test Merge', input='y')
    assert result.exit_code == 0

    def look_for_hours(date, project, hours):  # pragma: no cover
      for c in post_func.call_args_list:
        data = c[1]['data']

        if all([data.get('log_date') == date, data.get('project') == project, data.get('hours_worked') == hours]):
          return True

      return False

    def look_for_delete(id):
      for c in post_func.call_args_list:
        data = c[1]['data']

        if all([data.get('action') == 'delete', data.get('id') == id]):
          return True

      return False

    assert look_for_hours('05/18/2020', '10000', 6.0)
    assert look_for_hours('05/19/2020', '10000', 1.0)
    assert look_for_hours('05/20/2020', '10000', 3.0)
    assert look_for_delete(1)
    assert not look_for_delete(2)
    assert look_for_delete(3)

    post_func.reset_mock()
    result = run('addall', '5/18/2020', 'Test Project', '2', 'Test Merge', '--no-merge', input='y')
    assert result.exit_code == 0

    assert look_for_hours('05/18/2020', '10000', 2.0)
    assert look_for_hours('05/19/2020', '10000', 1.0)
    assert look_for_hours('05/20/2020', '10000', 2.0)
    assert not look_for_delete(1)
    assert not look_for_delete(2)
    assert not look_for_delete(3)

    post_func.reset_mock()
    result = run('addall', '5/18/2020', 'Test Project', '96', 'Test Merge', '--no-fill', input='y')
    assert result.exit_code == Error.INVALID_ARGUMENT
    assert result.output.startswith('Merging this item with other items is too many hours: 100.0')

    result = run('addall', '5/18/2020', 'Test Project', '96', 'Test Merge', '--no-fill', '--no-merge', input='y')
    assert result.exit_code == 0


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
