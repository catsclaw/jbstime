def test_holidays(run):
  result = run('holidays')
  assert result.exit_code == 0
  assert result.output.startswith('May 25, 2020: Memorial Day')
