from unittest.mock import patch

from jbstime.config import HOME
from jbstime.error import Error


def test_user_missing(run, no_config):
  with patch.dict('os.environ', {
    'JBS_TIMETRACK_PASS': 'foo',
  }):
    result = run('holidays', input='foo\n')
    assert result.exit_code == 0
    assert result.output.startswith('Username: foo\nMay 25, 2020: Memorial Day')

    result = run('--user', 'foo', 'holidays')
    assert result.exit_code == 0
    assert result.output.startswith('May 25, 2020: Memorial Day')


def test_pass_missing(run, no_config):
  with patch.dict('os.environ', {
    'JBS_TIMETRACK_USER': 'foo',
  }):
    result = run('holidays', input='foo\n')
    assert result.exit_code == 0
    assert result.output.startswith('Password: \nMay 25, 2020: Memorial Day')

    result = run('--pass', 'foo', 'holidays')
    assert result.exit_code == 0
    assert result.output.startswith('May 25, 2020: Memorial Day')


def test_bad_config(run, fs):
  fs.create_file(HOME() / 'config.yaml', contents='xxxxx')
  result = run('holidays')
  assert result.exit_code == Error.CONFIG_ERROR
  assert result.output.startswith('Error reading')


def test_holidays(run, fs):
  fs.create_file(HOME() / 'holidays.yaml', contents='2020-01-01: New Test Day')
  result = run('holidays')
  assert result.exit_code == 0
  assert result.output.startswith('May 25, 2020: Memorial Day')

  result = run('holidays', '--all')
  assert result.exit_code == 0
  assert result.output.startswith('Jan  1, 2020: New Test Day\nMay 25, 2020: Memorial Day')
