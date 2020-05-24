from unittest.mock import patch, PropertyMock

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


def test_login(run):
  result = run('--user', 'baduser', 'holidays')
  assert result.exit_code == Error.LOGIN_FAILED
  assert result.output == 'Login failed. Check your username and password.\n'


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

  result = run('timesheet', 'today')
  assert result.exit_code == 0
  assert result.output.startswith('\nTimesheet for May 24, 2020 (24.0 hours, unsubmitted)')

  result = run('timesheet', '5/24')
  assert result.exit_code == 0
  assert result.output.startswith('\nTimesheet for May 24, 2020 (24.0 hours, unsubmitted)')

  with patch('jbstime.api.Timesheet.items', new_callable=PropertyMock) as items_mock:
    items_mock.return_value = {}
    result = run('timesheet', 'today')
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
  result = run('add', 'today', 'Test Project', '8', 'Testing')
  assert result.exit_code == 0
  assert result.output == ''

  result = run('add', 'today', 'Test Project', 'foo', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Invalid hours: foo\n'

  result = run('add', 'today', 'Test Project', '100', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Too many hours: 100.0\n'

  result = run('add', 'today', 'Test Project', '8', '  ')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'No description provided\n'

  result = run('add', 'today', 'Missing Project', '8', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Invalid project: Missing Project\n'


def test_addall(run):
  result = run('addall', 'today', 'Test Project', '8', 'Testing')
  assert result.exit_code == 0
  assert result.output == ''


@patch('jbstime.api.Timesheet.hours', new_callable=PropertyMock)
@patch('jbstime.api.Timesheet.submit')
def test_submit(mock_submit, mock_hours, run):
  mock_hours.return_value = 40.0
  result = run('submit', input='y\n')
  assert result.exit_code == 0
  assert result.output == 'Submitted timesheet for May 24, 2020\n'
  mock_submit.assert_called_once()

  mock_hours.return_value = 38.0
  result = run('submit', input='n\n')
  assert result.exit_code == 0
  assert result.output == 'There are only 38.0 hours logged. Submit anyway? [y/N]: n\n'
  mock_submit.assert_called_once()

  mock_hours.return_value = 1.0
  result = run('submit', input='n\n')
  assert result.exit_code == 0
  assert result.output == 'There is only 1.0 hour logged. Submit anyway? [y/N]: n\n'
  mock_submit.assert_called_once()

  mock_hours.return_value = 0.0
  result = run('submit', input='n\n')
  assert result.exit_code == 0
  assert result.output == 'There is no time logged. Submit anyway? [y/N]: n\n'
  mock_submit.assert_called_once()

  result = run('submit', '5/17/2020')
  assert result.exit_code == Error.TIMESHEET_SUBMITTED


@patch('jbstime.api.Timesheet.delete_item')
def test_delete(mock_delete, run):
  result = run('delete', 'current', 'Test Project', '--all', input='n\n')
  assert result.exit_code == 0
  assert result.output == '5 items to delete\nAre you sure? [y/N]: n\n'
  mock_delete.assert_not_called()

  result = run('delete', 'current', 'Test Project', '--all', input='y\n')
  assert result.exit_code == 0
  assert result.output == '5 items to delete\nAre you sure? [y/N]: y\n'
  assert mock_delete.call_count == 5

  result = run('delete', '5/24/2020', 'Test Project')
  assert result.exit_code == 0
  assert result.output == 'No matching items\n'

  result = run('delete', 'current', 'Test Project', 'Missing Description', '--all')
  assert result.exit_code == 0
  assert result.output == 'No matching items\n'
