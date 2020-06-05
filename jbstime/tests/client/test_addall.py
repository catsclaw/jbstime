from datetime import date
from decimal import Decimal
from unittest.mock import call, patch, PropertyMock

from jbstime import req
from jbstime.api import TimesheetItem
from jbstime.error import Error


def look_for_hours(func, date, project, hours):
  for c in func.call_args_list:
    data = c[1]['data']

    if all([data.get('log_date') == date, data.get('project') == project, data.get('hours_worked') == hours]):
      return True

  return False


def look_for_delete(func, id):
  for c in func.call_args_list:
    data = c[1]['data']

    if all([data.get('action') == 'delete', data.get('id') == id]):
      return True

  return False


@patch('jbstime.api.Timesheet.add_item')
def test_addall(mock_add, run):
  mock_add.return_value = True
  result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing')
  assert result.exit_code == 0
  assert mock_add.call_count == 5
  mock_add.assert_has_calls([
    call(date(2020, 5, 18), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 19), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 20), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 21), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 22), 'Test Project', '8', 'Testing', fill=True, merge=True),
  ], any_order=True)


@patch('jbstime.api.Timesheet.add_item')
@patch('jbstime.api.list_holidays')
def test_holidays(mock_holidays, mock_add, run):
  mock_holidays.return_value = {
    date(2020, 5, 18): 'Holiday A',
  }
  mock_add.return_value = True
  result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing', input='y')
  assert result.exit_code == 0
  assert result.output.startswith('May 18, 2020 was Holiday A\n')
  assert 'Set holidays to time off?' in result.output
  assert mock_add.call_count == 5
  mock_add.assert_has_calls([
    call(date(2020, 5, 18), 'JBS - Paid Holiday', 8, 'Holiday A', fill=True, merge=True),
    call(date(2020, 5, 19), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 20), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 21), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 22), 'Test Project', '8', 'Testing', fill=True, merge=True),
  ], any_order=True)

  mock_holidays.return_value = {
    date(2020, 5, 18): 'Holiday A',
    date(2020, 5, 19): 'Holiday B',
  }
  mock_add.reset_mock()
  result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing', input='y')
  assert result.exit_code == 0
  assert result.output.startswith('May 18, 2020 was Holiday A and May 19, 2020 was Holiday B\n')
  assert 'Set holidays to time off?' in result.output
  assert mock_add.call_count == 5
  mock_add.assert_has_calls([
    call(date(2020, 5, 18), 'JBS - Paid Holiday', 8, 'Holiday A', fill=True, merge=True),
    call(date(2020, 5, 19), 'JBS - Paid Holiday', 8, 'Holiday B', fill=True, merge=True),
    call(date(2020, 5, 20), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 21), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 22), 'Test Project', '8', 'Testing', fill=True, merge=True),
  ], any_order=True)

  mock_holidays.return_value = {
    date(2020, 5, 18): 'Holiday A',
    date(2020, 5, 19): 'Holiday B',
    date(2020, 5, 20): 'Holiday C',
  }
  mock_add.reset_mock()
  result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing', input='n')
  assert result.exit_code == 0
  assert 'May 18, 2020 was Holiday A, May 19, 2020 was Holiday B, and May 20, 2020 was Holiday C\n' in result.output
  assert 'Set holidays to time off?' in result.output
  assert mock_add.call_count == 5
  mock_add.assert_has_calls([
    call(date(2020, 5, 18), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 19), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 20), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 21), 'Test Project', '8', 'Testing', fill=True, merge=True),
    call(date(2020, 5, 22), 'Test Project', '8', 'Testing', fill=True, merge=True),
  ], any_order=True)


@patch('jbstime.api.list_holidays')
@patch('jbstime.api.Timesheet.items', new_callable=PropertyMock)
def test_fill(mock_items, mock_holidays, run):
  mock_items.return_value = set([
    TimesheetItem(1, Decimal('4.0'), date(2020, 5, 18), 'Test Project', 'Test'),
    TimesheetItem(2, Decimal('7.0'), date(2020, 5, 19), 'Test Project', 'Test'),
    TimesheetItem(3, Decimal('1.0'), date(2020, 5, 20), 'Test Project', 'Test'),
    TimesheetItem(4, Decimal('1.0'), date(2020, 5, 20), 'Test Project', 'Test 2'),
    TimesheetItem(5, Decimal('8.0'), date(2020, 5, 22), 'Test Project', 'Test'),
  ])
  mock_holidays.return_value = {
    date(2020, 5, 18): 'Holiday A',
  }

  with patch('jbstime.req.post', wraps=req.post) as post_func:
    result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing', input='y')
    assert result.exit_code == 0
    assert 'Warning: no hours added to 2020-05-22' in result.output

    assert look_for_hours(post_func, '05/18/2020', '8', Decimal('4.0'))
    assert look_for_hours(post_func, '05/19/2020', '10000', Decimal('1.0'))
    assert look_for_hours(post_func, '05/20/2020', '10000', Decimal('6.0'))
    assert look_for_hours(post_func, '05/21/2020', '10000', Decimal('8.0'))
    assert not look_for_hours(post_func, '05/22/2020', '10000', Decimal('8.0'))

    post_func.reset_mock()
    result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing', '--no-fill', input='y')
    assert result.exit_code == 0
    assert 'Warning' not in result.output

    assert look_for_hours(post_func, '05/18/2020', '8', Decimal('8.0'))
    assert look_for_hours(post_func, '05/19/2020', '10000', Decimal('8.0'))
    assert look_for_hours(post_func, '05/20/2020', '10000', Decimal('8.0'))
    assert look_for_hours(post_func, '05/21/2020', '10000', Decimal('8.0'))
    assert look_for_hours(post_func, '05/22/2020', '10000', Decimal('8.0'))

  mock_items.return_value = set([
    TimesheetItem(1, Decimal('10.0'), date(2020, 5, 20), 'Test Project', 'Test'),
    TimesheetItem(2, Decimal('8.0'), date(2020, 5, 22), 'Test Project', 'Test'),
  ])
  result = run('addall', '5/18/2020', 'Test Project', '8', 'Testing', input='y')
  assert result.exit_code == 0
  assert '''Warning: the following dates are already full.
No additional hours were added to them.
  May 22, 2020 -   8.00 hours
  May 20, 2020 -  10.00 hours''' in result.output


@patch('jbstime.api.Timesheet.items', new_callable=PropertyMock)
def test_merge(mock_items, run):
  mock_items.return_value = set([
    TimesheetItem(1, Decimal('4.0'), date(2020, 5, 18), 'Test Project', 'Test Merge'),
    TimesheetItem(2, Decimal('7.0'), date(2020, 5, 19), 'Test Project', 'Test'),
    TimesheetItem(3, Decimal('1.0'), date(2020, 5, 20), 'Test Project', 'Test Merge'),
    TimesheetItem(4, Decimal('1.0'), date(2020, 5, 20), 'Test Project', 'Test 2'),
    TimesheetItem(5, Decimal('8.0'), date(2020, 5, 22), 'Test Project', 'Test'),
  ])

  with patch('jbstime.req.post', wraps=req.post) as post_func:
    result = run('addall', '5/18/2020', 'Test Project', '2', 'Test Merge', input='y')
    assert result.exit_code == 0

    assert look_for_hours(post_func, '05/18/2020', '10000', Decimal('6.0'))
    assert look_for_hours(post_func, '05/19/2020', '10000', Decimal('1.0'))
    assert look_for_hours(post_func, '05/20/2020', '10000', Decimal('3.0'))
    assert look_for_delete(post_func, 1)
    assert not look_for_delete(post_func, 2)
    assert look_for_delete(post_func, 3)

    post_func.reset_mock()
    result = run('addall', '5/18/2020', 'Test Project', '2', 'Test Merge', '--no-merge', input='y')
    assert result.exit_code == 0

    assert look_for_hours(post_func, '05/18/2020', '10000', Decimal('2.0'))
    assert look_for_hours(post_func, '05/19/2020', '10000', Decimal('1.0'))
    assert look_for_hours(post_func, '05/20/2020', '10000', Decimal('2.0'))
    assert not look_for_delete(post_func, 1)
    assert not look_for_delete(post_func, 2)
    assert not look_for_delete(post_func, 3)

    post_func.reset_mock()
    result = run('addall', '5/18/2020', 'Test Project', '96', 'Test Merge', '--no-fill', input='y')
    assert result.exit_code == Error.INVALID_ARGUMENT
    assert result.output.startswith('Merging this item with other items is too many hours: 100.0')

    result = run('addall', '5/18/2020', 'Test Project', '96', 'Test Merge', '--no-fill', '--no-merge', input='y')
    assert result.exit_code == 0
