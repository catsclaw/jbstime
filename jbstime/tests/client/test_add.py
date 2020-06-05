from decimal import Decimal
from unittest.mock import patch

from jbstime.api import PTO
from jbstime.error import Error


def test_add(run):
  result = run('add', '5/18/2020', 'Test Project', '8', 'Testing')
  assert result.exit_code == 0
  assert result.output == ''

  result = run('add', '5/18/2020', 'Test Project', 'foo', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Invalid hours: foo\n'

  result = run('add', '5/18/2020', 'Test Project', '100', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Too many hours: 100\n'

  result = run('add', '5/18/2020', 'Test Project', '--', '-5', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Hours cannot be negative: -5\n'

  result = run('add', '5/18/2020', 'Test Project', '0', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Hours cannot be 0\n'

  result = run('add', '5/18/2020', 'Test Project', '8', '  ')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'No description provided\n'

  result = run('add', '5/18/2020', 'Missing Project', '8', 'Testing')
  assert result.exit_code == Error.INVALID_ARGUMENT
  assert result.output == 'Invalid project: Missing Project\n'


@patch('jbstime.api.pto')
def test_pto(mock_pto, run):
  mock_pto.return_value = PTO(
    balance=Decimal('9.5'),
    cap=Decimal('10.0'),
    earned=Decimal('100.0'),
    used=Decimal('90.5'),
    accrual=110
  )

  result = run('add', '5/18/2020', 'Test Project', '8', 'Testing')
  assert result.exit_code == 0
  assert 'exceeds your PTO cap\nCurrent timesheet puts you at 12.41. Cap is 10.0' in result.output
