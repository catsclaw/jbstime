from unittest.mock import patch

from jbstime.error import Error


def test_user_pass(run):
  with patch('pathlib.Path.open') as mock_open:
    mock_open.side_effect = FileNotFoundError

    with patch.dict('os.environ', {
      'JBS_TIMETRACK_USER': '',
    }):
      result = run('holidays', input='foo')
      assert result.exit_code == 0
      assert result.output.startswith('Username: foo\nMay 25, 2020: Memorial Day')

      result = run('--user', 'foo', 'holidays')
      assert result.exit_code == 0
      assert result.output.startswith('May 25, 2020: Memorial Day')

    with patch.dict('os.environ', {
      'JBS_TIMETRACK_PASS': '',
    }):
      result = run('holidays', input='foo')
      assert result.exit_code == 0
      assert result.output.startswith('Password: \nMay 25, 2020: Memorial Day')

      result = run('--pass', 'foo', 'holidays')
      assert result.exit_code == 0
      assert result.output.startswith('May 25, 2020: Memorial Day')

  with patch('pathlib.Path.open') as mock_open:
    mock_open.return_value = 'xxx'
    result = run('holidays')
    assert result.exit_code == Error.CONFIG_ERROR
    assert result.output.startswith('Error reading')
