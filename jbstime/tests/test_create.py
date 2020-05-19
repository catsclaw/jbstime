from jbstime.error import Error


def test_create(run):
  result = run('create', '5/24')
  assert result.exit_code == 0
  assert result.output == 'Created timesheet for May 24, 2020\n'

  result = run('create', '5/10')
  assert result.exit_code == Error.TIMESHEET_EXISTS
  assert result.output == 'A timesheet already exists for May 10, 2020\n'
