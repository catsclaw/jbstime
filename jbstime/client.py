from datetime import date, datetime, timedelta
from decimal import Decimal
import sys

import click

from . import api, config as config_
from .api import Timesheet
from .dates import date_fmt, date_fmt_pad_day, date_from_user_date, find_sunday
from .error import Error


def _exec():  # pragma: no cover
  try:
    return cli()
  except Exception as e:
    click.echo(f'Unexpected error: {e}', err=True)
    sys.exit(Error.UNEXPECTED_ERROR)


def check_pto(timesheet, full_report=False):
  pto_info = api.pto()
  added_hours = Decimal('0')
  removed_hours = Decimal('0')
  for i in timesheet.items:
    if i.project.startswith('JBS - PTO'):
      removed_hours += i.hours
    else:
      added_hours += i.hours

  new_pto = pto_info.balance + (added_hours / pto_info.accrual * 8) - removed_hours

  def pl(x):
    if 0.999 < x < 1.001:
      return '1 hour'

    return f'{x} hours'

  if full_report:
    click.echo(f'You have {pl(pto_info.balance)} remaining')
    click.echo(f'You have earned {pl(pto_info.earned)} and used {pl(pto_info.used)}')
    click.echo(f'You earn a day for every {pl(pto_info.accrual)}')
    click.echo(f'You are capped at {pl(pto_info.cap)}')

  if pto_info.cap <= new_pto and not timesheet.locked:
    click.echo('Warning: current additional hours exceeds your PTO cap')

    current_str = f'Current timesheet puts you at {new_pto:.2f}.'
    if not full_report:
      current_str += f' Cap is {pto_info.cap}.'

    click.echo(current_str)


@click.group()
@click.option('-u', '--user', 'username')
@click.option('-p', '--pass', 'password')
@click.pass_context
def cli(ctx, username, password):
  """
    Commands for managing JBS timesheets.

    In general, any place a timesheet date is called for, you can use any date
    that is covered by that timesheet. So a timesheet for Sunday, July 20th
    would accept any date from 7/14 to 7/20. And "current" and "today" are
    synonyms for the current date.

    You can specify a username and password by running `config`, or by
    creating JBS_TIMESHEET_USER and JBS_TIMESHEET_PASS environmental
    variables, or by using the --user and --pass options. If all else fails,
    you will be prompted to enter them on the command line.
  """

  ctx.ensure_object(dict)
  ctx.obj['cmd_username'] = username
  ctx.obj['cmd_password'] = password
  ctx.obj['logged_in'] = False


@cli.command()
@click.argument('date')
@click.argument('project')
@click.argument('hours')
@click.argument('description')
@click.option('--merge/--no-merge', default=True)
def add(date, project, hours, description, merge):
  """
    Adds an entry to a timesheet.

    DATE is the date of the entry. This will automatically select the correct
    timesheet. --merge (the default) will delete existing items with the same
    project and description and combine those hours into a single item.
    --no-merge disables this feature.
  """

  timesheet = Timesheet.from_user_date(date)
  date = date_from_user_date(date)
  timesheet.add_item(date, project, hours, description, fill=False, merge=merge)
  if Timesheet.latest() == timesheet:
    timesheet.reload()
    check_pto(timesheet)


@cli.command()
def config():
  """
    Creates a config file.

    This asks for the username and password on the command line, then creates
    a config file so they do not need to be provided manually. If a config
    file already exists this will replace the existing username and password.

    WARNING: This stores data - including your password - in plaintext in your
    home directory. If security is a concern, you should provide the password
    on the command line or in an environmental variable.
  """
  username = click.prompt('Username')
  password = click.prompt('Password', hide_input=True)

  config_.create_config(username, password)
  click.echo(f'Config written to {config_.config_path()}')


@cli.command()
@click.argument('date')
@click.argument('project')
@click.argument('hours')
@click.argument('description')
@click.option('--fill/--no-fill', default=True)
@click.option('--merge/--no-merge', default=True)
def addall(date, project, hours, description, fill, merge):
  """
    Adds an entry to every workday on a timesheet. Useful for quickly filling
    out duplicate entries.

    DATE is the date of the timesheet. --fill (the default) will ensure if
    time is already recorded that additional time does not extend beyond an 8
    hour day. --merge (also the default) will delete existing items with the
    same project and description and combine those hours into a single item.
    --no-fill and --no-merge disables these feature.

    In the event that any of the days overlap with JBS holidays, you will be
    prompted with an option to fill those out with paid holiday time instead.
  """
  timesheet = Timesheet.from_user_date(date)

  set_holidays = False
  dates = [timesheet.date - timedelta(days=x) for x in range(2, 7)]
  holidays = api.list_holidays()
  conflicts = sorted((d, h) for d, h in holidays.items() if d in dates)
  if conflicts:
    today = datetime.now().date()
    cstr = ''

    for i, (d, h) in enumerate(conflicts):
      if i > 0:
        if len(conflicts) != 2:
          cstr += ','

        cstr += ' '

        if i == (len(conflicts) - 1):
          cstr += 'and '

      verb = 'was' if d < today else 'is'
      cstr += f'{date_fmt(d)} {verb} {h}'

    click.echo(cstr)
    set_holidays = click.confirm('Set holidays to time off?')

  # Add the same info to Monday through Friday
  results = []
  with click.progressbar(dates) as item_dates:
    for d in item_dates:
      if set_holidays and d in holidays:
        results.append([d, timesheet.add_item(d, 'JBS - Paid Holiday', 8, holidays[d], fill=fill, merge=merge)])
      else:
        results.append([d, timesheet.add_item(d, project, hours, description, fill=fill, merge=merge)])

  count_errors = sum(r is not True for d, r in results)
  if count_errors == 1:
    for d, r in results:
      if r is not True:
        click.echo(f'Warning: no hours added to {d}. It already has {r} hours.')
        break
  elif count_errors > 0:
    click.echo('Warning: the following dates are already full.')
    click.echo('No additional hours were added to them.')
    for d, r in results:
      if r is not True:
        click.echo(f'  {date_fmt_pad_day(d)} - {r:>6.2f} hours')

  if Timesheet.latest() == timesheet:
    timesheet.reload()
    check_pto(timesheet)


@cli.command()
@click.argument('date')
@click.argument('project')
@click.argument('description', required=False)
@click.option('--all', is_flag=True, help='Apply to all days on the timesheet')
def delete(date, project, description, all):
  """
    Deletes an entry or entries from a timesheet.

    DATE is the date of the entry, or if the --all flag is specified, the date
    of the timesheet. This will match everything with a specific project (and
    description, if that is specified). You can use "all" as the project name,
    in which case it will match all projects.

    You will be prompted with the number of affected entries and given a chance
    to confirm the deletion.
  """

  timesheet = Timesheet.from_user_date(date)
  item_date = None if all else date_from_user_date(date)
  project = project.lower()
  description = description.lower() if description else None

  to_delete = set()
  for i in timesheet.items:
    if item_date and item_date != i.date:
      continue

    if project == 'all' or project == i.project.lower():
      if description and description != i.description.lower():
        continue

      to_delete.add(i)

  if not len(to_delete):
    click.echo('No matching items')
    sys.exit()

  count = len(to_delete)
  plural = 's' if count > 1 else ''
  click.echo(f'{count} item{plural} to delete')
  if not click.confirm('Are you sure?'):
    return

  with click.progressbar(to_delete) as items:
    for i in items:
      timesheet.delete_item(i.id)


@cli.command()
@click.argument('date', default='current')
def create(date):
  """
    Creates a timesheet.

    If DATE is not specified, uses the current date.
  """

  date = date_from_user_date(date)
  timesheet_date = find_sunday(date)
  Timesheet.create(timesheet_date)
  click.echo(f'Created timesheet for {date_fmt(timesheet_date)}')


@cli.command()
@click.argument('date', default='current')
def submit(date):
  """
    Submits a timesheet.

    This will warn you if there are fewer than 40 hours recorded. Timesheets
    cannot be edited after they've been submitted.
  """
  timesheet = Timesheet.from_user_date(date)
  if timesheet.locked:
    click.echo(f'The timesheet for {date_fmt(timesheet.date)} has already been submitted', err=True)
    sys.exit(Error.TIMESHEET_SUBMITTED)

  if timesheet.hours < 39.9:
    if timesheet.hours < 0.01:
      msg = 'There is no time logged. Submit anyway?'
    else:
      plural = 'hours' if timesheet.hours > 1 else 'hour'
      verb = 'is' if 0.09 < timesheet.hours < 1.01 else 'are'
      msg = f'There {verb} only {timesheet.hours} {plural} logged. Submit anyway?'

    if not click.confirm(msg):
      sys.exit()

  timesheet.submit()
  click.echo(f'Submitted timesheet for {date_fmt(timesheet.date)}')


@cli.command()
@click.option('--limit', default='5', show_default=True, help='Number to show, or "all"')
def timesheets(limit):
  """
    Lists existing timesheets, most recent first.
  """

  dates = Timesheet.list()
  if limit == 'all':
    limit = len(dates)
  else:
    try:
      limit = int(limit)
    except ValueError:
      click.echo(f'Invalid limit: {limit}', err=True)
      sys.exit(Error.INVALID_ARGUMENT)

  if limit:
    limit -= 1

  for i, ts in enumerate(dates.values()):
    if i == limit:
      break

    lock = '  (unsubmitted)' if not ts.locked else ''
    click.echo(f'{date_fmt_pad_day(ts.date)}  {ts.hours:>6.2f}{lock}')


@cli.command()
@click.argument('search', required=False)
@click.option('--all', is_flag=True, help='Include non-favorited projects')
def projects(search, all):
  """
    Lists projects.

    If SEARCH is specified, this will only list projects which include the
    search string (case-insensitive). By default, this only lists projects
    you have favorited.
  """

  if search:
    search = search.lower()

  for project in api.list_projects().values():
    if search and search not in project.name.lower():
      continue

    if all or project.favorite:
      click.echo(project.name)


@cli.command()
@click.option('--all', is_flag=True, help='List all holidays, including historic ones')
def holidays(all):
  """
    Lists JBS holidays. The website does not list past holidays, but if there
    is a .jbstime directory in the user's home directory past dates will be
    cached and available to the program. By default only future holidays and
    the past two weeks will be displayed, but all of them can be dispayed with
    the "--all" option.
  """

  if all:
    start_date = date(1970, 1, 1)
  else:
    start_date = (datetime.now() - timedelta(weeks=2)).date()

  holidays = api.list_holidays()
  for d in sorted(holidays):
    if d < start_date:
      continue

    click.echo(f'{date_fmt_pad_day(d)}: {holidays[d]}')


@cli.command()
def pto():
  """
    Lists your PTO information.
  """
  check_pto(Timesheet.latest(), full_report=True)


@cli.command()
@click.argument('date', default='latest')
def timesheet(date):
  """
    Show the specified timesheet.

    If DATE is not specified, this shows the latest timesheet.
  """
  if date == 'latest':
    timesheet = Timesheet.latest()
  else:
    timesheet = Timesheet.from_user_date(date)

  if not timesheet.items:
    click.echo(f'No hours added to the timesheet for {date_fmt(timesheet.date)}')
    sys.exit()

  plural = 's' if timesheet.hours > 1.01 else ''
  unsubmitted = ', unsubmitted' if not timesheet.locked else ''
  title = f'Timesheet for {date_fmt(timesheet.date)} ({timesheet.hours} hour{plural}{unsubmitted})'

  click.echo()
  click.echo(title)
  click.echo('-' * len(title))
  dates = set(x.date for x in timesheet.items)
  for d in sorted(dates):
    click.echo(f'{d:%b} {d.day:>2}, {d.year} ({d:%A})')
    items = sorted(x for x in timesheet.items if x.date == d)
    for i in items:
      click.echo(f'{i.project:>30}  {i.hours:>6.2f}  {i.description}')

    click.echo()
