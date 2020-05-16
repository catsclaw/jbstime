from datetime import timedelta
import os
import sys

import click

from . import req
from .api import list_holidays, list_projects, login, Timesheet
from .config import load_config
from .dates import date_fmt, date_fmt_pad_day, date_from_user_date, find_sunday
from .error import Error


@click.group()
@click.option('-u', '--user', 'username')
@click.option('-p', '--pass', 'password')
def cli(username, password):
  config = load_config()

  username = username or config['username']
  password = password or config['password']

  if not username:
    username = click.prompt('Username')

  if not password:
    password = click.prompt('Password', hide_input=True)

  if not login(username, password):
    click.echo('Login failed. Check your username and password.', err=True)
    sys.exit(Error.LOGIN_FAILED)

@cli.command()
@click.argument('date')
@click.argument('project')
@click.argument('hours')
@click.argument('description')
def add(date, project, hours, description):
  timesheet = Timesheet.from_user_date(date)
  date = date_from_user_date(date)
  timesheet.add_item(date, project, hours, description)


@cli.command()
@click.argument('date')
@click.argument('project')
@click.argument('hours')
@click.argument('description')
def addall(date, project, hours, description):
  timesheet = Timesheet.from_user_date(date)

  set_holidays = False

  dates = [timesheet.date - timedelta(days=x) for x in range(2, 7)]
  holidays = list_holidays()
  conflicts = sorted((d, h) for d, h in holidays.items() if d in dates)
  if conflicts:
    cstr = ''

    for i, (d, h) in enumerate(conflicts):
      if i > 0:
        if len(conflicts) != 2:
          cstr += ','

        cstr += ' '

        if i == (len(conflicts) - 1):
          cstr += 'and '

      cstr += f'{date_fmt(d)} is {h}'

    click.echo(cstr)
    set_holidays = click.confirm('Set holidays to time off?')

  # Add the same info to Monday through Friday
  with click.progressbar(dates) as item_dates:
    for d in item_dates:
      if set_holidays and d in holidays:
        timesheet.add_item(d, 'JBS - Paid Holiday', 8.0, holidays[d])
      else:
        timesheet.add_item(d, project, hours, description)


@cli.command()
@click.argument('date')
@click.argument('project')
@click.argument('description', required=False)
@click.option('--all', is_flag=True)
def delete(date, project, description, all):
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
@click.argument('date', default='today')
def create(date):
  date = date_from_user_date(date)
  timesheet_date = find_sunday(date)
  timesheet_id = Timesheet.create(timesheet_date)
  click.echo(f'Created timesheet for {date_fmt(timesheet_date)}')


@cli.command()
@click.argument('date', default='today')
def submit(date):
  timesheet = Timesheet.from_user_date(date)
  if timesheet.locked:
    click.echo(f'The timesheet for {date_fmt(timesheet.date)} has already been submitted', err=True)
    sys.exit(Error.TIMESHEET_SUBMITTED)

  if timesheet.hours < 39.9:
    if timesheet.hours < 0.01:
      msg = 'There is no time logged. Submit anyway?'
    else:
      plural = 's' if timesheet.hours > 1 else ''
      verb = 'is' if 0.09 < timesheet.hours < 1.01 else 'are'
      msg = f'There {verb} only {timesheet.hours} hour{plural} logged. Submit anyway?'

    if not click.confirm(msg):
      sys.exit()

  timesheet.submit()
  click.echo(f'Submitted timesheet for {date_fmt(timesheet.date)}')


@cli.command()
@click.option('--limit', default='5', show_default=True, help='Number to show, or "all"')
def timesheets(limit):
  dates = Timesheet.list()
  if limit == 'all':
    limit = len(dates)
  else:
    try:
      limit = int(limit)
    except ValueError:
      click.echo(f'Invalid limit: {limit}', err=True)
      sys.exit(Error.INVALID_ARGUMENT)

  for i, ts in enumerate(dates.values()):
    if i == limit:
      break

    lock = '  (unsubmitted)' if not ts.locked else ''
    click.echo(f'{date_fmt_pad_day(ts.date)}  {ts.hours:>6.2f}{lock}')


@cli.command()
@click.argument('search', required=False)
@click.option('--all', is_flag=True)
def projects(search, all):
  if search:
    search = search.lower()

  for project in list_projects().values():
    if search and not search in project.name.lower():
      continue

    if all or project.favorite:
      click.echo(project.name)


@cli.command()
def holidays():
  for date, holiday in list_holidays().items():
    click.echo(f'{date_fmt_pad_day(date)}: {holiday}')


@cli.command()
@click.argument('date', default='latest')
def timesheet(date):
  if date == 'latest':
    timesheet = Timesheet.latest()
  else:
    timesheet = Timesheet.from_user_date(date)

  if not timesheet.items:
    click.echo(f'No hours added to the timesheet for {date_fmt(timesheet.date)}')
    sys.exit()


  plural = 's' if timesheet.hours > 1.001 else ''
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
