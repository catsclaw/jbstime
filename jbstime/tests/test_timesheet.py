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
