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
