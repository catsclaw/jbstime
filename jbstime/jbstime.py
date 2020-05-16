from datetime import timedelta
import os
import sys

import click

from . import req
from .api import list_holidays, list_projects, login, Timesheet
from .dates import date_fmt, date_fmt_pad_day, date_from_user_date, find_sunday
from .error import Error


@click.group()
@click.option('-u', '--user', 'username')
@click.option('-p', '--pass', 'password')
def cli(username, password):
  if not username:
    username = os.environ.get('JBS_TIMETRACK_USER')

  if not password:
    password = os.environ.get('JBS_TIMETRACK_PASS')

  if not login(username, password):
    click.echo('Login failed. Check your username and password.', err=True)


@cli.command()
@click.argument('date')
@click.argument('project')
@click.argument('hours')
@click.argument('description')
def add(date, project, hours, description):
  timesheet = Timesheet.from_user_date(date)
  date = date_from_user_date(date)

  project = list_projects().get(project.lower())
  if not project:
    click.echo(f'Invalid project: {project}', err=True)
    sys.exit(Error.INVALID_ARGUMENT)

  try:
    hours = float(hours)
  except ValueError:
    click.echo(f'Invalid hours: {hours}', err=True)
    sys.exit(Error.INVALID_ARGUMENT)

  if hours > 99.0:
    click.echo(f'Too many hours: {hours}', err=True)
    sys.exit(Error.INVALID_ARGUMENT)

  description = description.strip()
  if not description:
    click.echo('No description provided', err=True)
    sys.exit(Error.INVALID_ARGUMENT)

  r = req.post(f'/timesheet/{timesheet.id}/', data={
    'log_date': date.strftime('%m/%d/%Y'),
    'project': project.id,
    'hours_worked': hours,
    'description': description,
    'ticket': '',
    'billing_type': 'M',
    'parent_ticket': '',
    'undefined': '',
  }, xhr=True)


@cli.command()
@click.argument('date')
@click.argument('project')
@click.argument('hours')
@click.argument('description')
def addall(date, project, hours, description):
  timesheet = Timesheet.from_user_date(date)

  project = list_projects().get(project.lower())
  if not project:
    click.echo(f'Invalid project: {project}', err=True)
    sys.exit(Error.INVALID_ARGUMENT)

  try:
    hours = float(hours)
  except ValueError:
    click.echo(f'Invalid hours: {hours}', err=True)
    sys.exit(Error.INVALID_ARGUMENT)

  if hours > 99.0:
    click.echo(f'Too many hours: {hours}', err=True)
    sys.exit(Error.INVALID_ARGUMENT)


  description = description.strip()
  if not description:
    click.echo('No description provided', err=True)
    sys.exit(Error.INVALID_ARGUMENT)

  # Add the same info to Monday through Friday
  with click.progressbar([timesheet.date - timedelta(days=x) for x in range(2, 7)]) as dates:
    for d in dates:
      r = req.post(f'/timesheet/{timesheet.id}/', data={
        'log_date': d.strftime('%m/%d/%Y'),
        'project': project.id,
        'hours_worked': hours,
        'description': description,
        'ticket': '',
        'billing_type': 'M',
        'parent_ticket': '',
        'undefined': '',
      }, xhr=True)


@cli.command()
@click.argument('date')
@click.argument('project')
@click.argument('description', required=False)
def delete(date, project, description):
  timesheet = timesheet_from_user_date(date)

  to_delete = set()
  for i in timesheet.items:
    if i.project.lower() == project.lower():
      if description and description.lower() != i.description.lower():
        continue

      to_delete.add(i)

  if not len(to_delete):
    click.echo('No matching items')
    sys.exit()

  click.echo(f'{len(to_delete)} items to delete')
  if not click.confirm('Are you sure?'):
    return

  with click.progressbar(to_delete) as items:
    for i in items:
      req.post(f'/timesheet/{timesheet.id}/', data={
        'id': i.id,
        'action': 'delete',
      }, xhr=True)


@cli.command()
@click.argument('date', default='today')
def create(date):
  date = date_from_user_date(date)
  timesheet_date = find_sunday(date)
  timesheet_id = create_new_sheet(timesheet_date)
  click.echo(f'Created timesheet for {date_fmt(timesheet_date)}')


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
def projects():
  for project in list_projects().values():
    if project.favorite:
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

  hour_sum = sum(x.hours for x in timesheet.items)
  title = f'Timesheet for {date_fmt(timesheet.date)} ({hour_sum} hours)'

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
