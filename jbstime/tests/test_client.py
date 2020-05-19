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


def test_timesheets(run):
  result = run('timesheets')
  assert result.exit_code == 0
  assert result.output.startswith('May 24, 2020   24.00  (unsubmitted)\nMay 17, 2020   40.00\n')
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


def test_addall(run):
  result = run('addall', 'today', 'Test Project', '8', 'Testing')
  assert result.exit_code == 0
  assert result.output == ''


def test_submit(run):
  result = run('submit', input='y\n')
  assert result.exit_code == 0
  assert result.output.endswith('Submitted timesheet for May 24, 2020\n')

  result = run('submit', input='n\n')
  assert result.exit_code == 0
  assert result.output == 'There are only 24.0 hours logged. Submit anyway? [y/N]: n\n'


def test_delete(run):
  result = run('delete', 'current', 'Test Project', '--all', input='y\n')
  assert result.exit_code == 0
  assert result.output == '5 items to delete\nAre you sure? [y/N]: y\n'
