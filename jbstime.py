from collections import namedtuple
from datetime import datetime, timedelta
from enum import IntEnum
import sys

from bs4 import BeautifulSoup
import click
from dateutil.parser import parse
from dateutil.parser._parser import ParserError
import requests


class Error(IntEnum):
  INVALID_ARGUMENT = 1
  TIMESHEET_MISSING = 2
  UNPARSABLE_DATE = 3
  TIMESHEET_EXISTS = 4


s = requests.Session()


def _get(url, *args, **kw):
  return _req('get', url, *args, **kw)


def _post(url, data, *args, referer=None, **kw):
  # If we're doing a post, we need a csrf token
  referer = referer or url
  r = s.get('https://timetrack.jbecker.com' + referer)
  csrf_token = r.cookies['csrftoken']

  data['csrfmiddlewaretoken'] = csrf_token
  kw.setdefault('headers', {})
  kw['headers']['Referer'] = referer

  return _req('post', url, *args, data=data, **kw)


def _req(method, url, *args, **kw):
  url = 'https://timetrack.jbecker.com' + url
  print('**', kw)
  return s.request(method, url, *args, **kw)


def date_fmt(d, pad_day=False):
  if pad_day:
    return f'{d:%b} {d.day:>2}, {d.year}'
  else:
    return f'{d:%b} {d.day}, {d.year}'


def find_sunday(d):
  return d + timedelta(days=(6 - d.weekday()))


def parse_timesheet_date(d):
  try:
    d = parse(d).date()
  except ParserError:
    click.echo(f'Can\'t parse date: {d}', err=True)
    sys.exit(Error.UNPARSABLE_DATE)

  return find_sunday(d)


def login(username, password):
  r = _post('/accounts/login/', data={
    'username': username,
    'password': password,
    'next': '/?all=1',
  }, referer='/accounts/login/')

  r.raise_for_status()
  if 'Your username and password didn\'t match' in r.text:
    return False

  return True


Timesheet = namedtuple('Timesheet', 'locked hours work_hours date id')


def list_timesheets():
  r = _get('/?all=1')
  r.raise_for_status()

  doc = BeautifulSoup(r.text, 'html.parser')
  dates = {}
  for row in doc.find('table', attrs={'class': 'latest-timesheet-table'}).find_all('tr'):
    data = row.find_all('td')
    if not data:
      continue

    timesheet_date = datetime.strptime(data[1].contents[0][12:], '%m/%d/%Y').date()
    dates[timesheet_date] = Timesheet(
      (data[0].find('span')['class'] + [None])[0]  == 'locked',
      float(data[2].contents[0]),
      float(data[3].contents[0]),
      timesheet_date,
      data[5].find('a')['href'][11:-1]
    )

  return dates


TimesheetItem = namedtuple('TimesheetItem', 'id hours date project description')
Project = namedtuple('Project', 'id name favorite')
TimesheetDetails = namedtuple('TimesheetDetails', 'items projects')


def timesheet_detail(ts_id):
  r = _get(f'/timesheet/{ts_id}/')
  r.raise_for_status()

  doc = BeautifulSoup(r.text, 'html.parser')
  items = set()
  for row in doc.find('div', attrs={'class': 'tableholder'}).find_all('tr'):
    if not row.get('id'):
      continue

    items.add(TimesheetItem(
      row.find('input', attrs={'name': 'id'})['value'],
      float(row.find('input', attrs={'name': 'hours_worked'})['value']),
      datetime.strptime(row.find('input', attrs={'name': 'log_date'})['value'], '%m/%d/%Y').date(),
      row.find('select', attrs={'name': 'project'}).find('option', selected='selected').contents[0],
      row.find('textarea', attrs={'name': 'description'}).contents[0]
    ))

  projects = {}
  for option in doc.find('select', id='fav_projects').find_all('option'):
    name = option.contents[0]
    projects[name.lower()] = Project(
      option['value'],
      name,
      option.get('selected') == 'selected'
    )

  return TimesheetDetails(items, projects)


def create_new_sheet(date):
  r = _post('/timesheet/', data={
    'csrfmiddlewaretoken': token,
    'newsheet': date.strftime('%m/%d/%Y'),
  }, referer='/accounts/login/?next=/')

  r.raise_for_status()
  if 'That timesheet already exists' in r.text:
    click.echo(f'A timesheet already exists for {date_fmt(date)}', err=True)
    sys.exit(Error.TIMESHEET_EXISTS)


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
  try:
    date = parse(date).date()
    timesheet_date = find_sunday(date)
  except ParserError:
    click.echo(f'Can\'t parse date: {data[0]}', err=True)
    sys.exit(Error.UNPARSABLE_DATE)

  timesheets = list_timesheets()
  if not timesheets:
    click.echo('No timesheets found', err=True)
    sys.exit(Error.TIMESHEET_MISSING)

  timesheet = timesheets.get(timesheet_date)
  if not timesheet:
    click.echo(f'No timesheet found for {date_fmt(timesheet_date)}', err=True)
    sys.exit(Error.TIMESHEET_MISSING)

  detail = timesheet_detail(timesheet.id)
  project = detail.projects.get(project.lower())
  if not project:
    click.echo(f'Invalid project: {project}', err=True)
    sys.exit(Error.INVALID_ARGUMENT)

  try:
    hours = float(hours)
  except ValueError:
    click.echo(f'Invalid hours: {hours}', err=True)
    sys.exit(Error.INVALID_ARGUMENT)

  description = description.strip()
  if not description:
    click.echo('No description provided', err=True)
    sys.exit(Error.INVALID_ARGUMENT)

  r = _post(f'/timesheet/{timesheet.id}/', params={
    'log_date': date.strftime('%m/%d/%Y'),
    'project': project.id,
    'hours_worked': hours,
    'description': description,
    'ticket': '',
    'billing_type': 'M',
    'parent_ticket': '',
    'undefined': '',
  })

# jbstime add 5/3 "Petco - Mobile Squad" 8 "This is my description"
# jbstime add 5/1 5/3 "Petco - Mobile Squad" 8 "This is my description"

# csrf_token: 5Tv6lZ8LWJM4ea7rWiXnDNEtecxe7b6a
# log_date: 05/15/2020
# project: 693
# hours_worked: 1
# description: Architecture
# ticket:
# billing_type: M
# parent_ticket:
# undefined:


@cli.command()
@click.argument('date', default='current')
def create(date):
  if date == 'current':
    date = find_sunday(datetime.now().date())
  else:
    date = parse_timesheet_date(date)

  timesheet_id = create_new_sheet(date)
  click.echo(f'Created timesheet for {date_fmt(date)}')


@cli.command()
@click.option('--limit', default='5', show_default=True, help='Number to show, or "all"')
def timesheets(limit):
  dates = list_timesheets()
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
    click.echo(f'{date_fmt(ts.date, pad_day=True)}  {ts.hours:>6.2f}{lock}')


@cli.command()
@click.argument('date', default='latest')
def timesheet(date):
  timesheets = list_timesheets()
  if not timesheets:
    click.echo('No timesheets found', err=True)
    sys.exit(Error.TIMESHEET_MISSING)

  if date == 'latest':
    timesheet = list(timesheets.values())[0]
  else:
    date = parse_timesheet_date(date)

    try:
      timesheet = timesheets[date]
    except KeyError:
      click.echo(f'No timesheet found for {date_fmt(date)}', err=True)
      sys.exit(Error.TIMESHEET_MISSING)

  detail = timesheet_detail(timesheet.id)

  if not detail.items:
    click.echo(f'No hours added to the timesheet for {date_fmt(timesheet.date)}')
    sys.exit()

  hour_sum = sum(x.hours for x in detail.items)
  title = f'Timesheet for {date_fmt(timesheet.date)} ({hour_sum} hours)'

  click.echo()
  click.echo(title)
  click.echo('-' * len(title))
  dates = set(x.date for x in detail.items)
  for d in sorted(dates):
    click.echo(f'{d:%b} {d.day:>2}, {d.year} ({d:%A})')
    items = sorted(x for x in detail.items if x.date == d)
    for i in items:
      click.echo(f'{i.project:>30}  {i.hours:>6.2f}  {i.description}')

    click.echo()


if __name__ == '__main__':
  cli()
