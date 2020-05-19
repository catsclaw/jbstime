from jbstime.error import Error


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
