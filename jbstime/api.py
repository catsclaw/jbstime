from collections import namedtuple
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
import sys

from bs4 import BeautifulSoup
import click

from . import config, req
from .dates import date_fmt, date_from_user_date, find_sunday
from .error import Error


_timesheets = None
_holidays = None
_projects = None
_pto = None


TimesheetItem = namedtuple('TimesheetItem', 'id hours date project description')
PTO = namedtuple('PTO', 'balance cap earned used accrual')
Project = namedtuple('Project', 'id name favorite')


def _clear():
  global _timesheets, _projects, _holidays, _pto
  _timesheets = None
  _projects = None
  _holidays = None
  _pto = None


def list_projects():
  if _projects is None:
    latest = Timesheet.latest()
    latest._load_details()

  return _projects


def list_holidays():
  if _holidays is None:
    Timesheet._load()

  return _holidays


def pto():
  if _pto is None:
    Timesheet._load()

  return _pto


class Timesheet:
  def __init__(self, id, date, hours, work_hours, locked):
    self.id = id
    self.date = date
    self._hours = hours
    self.work_hours = work_hours
    self.locked = locked

    self._items = None

  @classmethod
  def list(cls):
    if _timesheets is None:
      cls._load()

    return _timesheets

  @classmethod
  def _load(cls):
    global _holidays, _timesheets, _pto

    r = req.get('/?all=1')

    doc = BeautifulSoup(r.text, 'html.parser')

    _timesheets = {}
    for row in doc.find('table', attrs={'class': 'latest-timesheet-table'}).find_all('tr'):
      data = row.find_all('td')
      if not data:
        continue

      timesheet_date = datetime.strptime(data[1].contents[0][12:], '%m/%d/%Y').date()
      _timesheets[timesheet_date] = Timesheet(
        id=data[5].find('a')['href'][11:-1],
        date=timesheet_date,
        hours=Decimal(data[2].contents[0]),
        work_hours=Decimal(data[3].contents[0]),
        locked=(data[0].find('span')['class'] + [None])[0] == 'locked',
      )

    _pto = PTO(
      balance=Decimal(doc.find('td', text='Previous PTO Balance').find_next_sibling('td').contents[0]),
      cap=int(doc.find('td', text=re.compile(r'^PTO is capped at \d+ hours$')).contents[0][17:-6]),
      earned=Decimal(doc.find('td', text='Total PTO Earned').find_next_sibling('td').contents[0]),
      used=Decimal(doc.find('td', text='Total PTO Used').find_next_sibling('td').contents[0]),
      accrual=int(doc.find('td', text='Current PTO Accrual Rate').find_next_sibling('td').contents[0].split(' ')[0])
    )

    today = datetime.now().date()
    _holidays = {k: v for k, v in config.load_holidays().items() if k <= today}

    for td in doc.find('div', attrs={'class': 'ptoplaceholder'}).find_all('td'):
      if td.contents[0] == 'Upcoming Company Holidays':
        for holiday in td.find_next_sibling('td').find_all('p'):
          h, d = holiday.contents[0].split(' - ')
          _holidays[datetime.strptime(d, '%m/%d/%Y').date()] = h

    config.save_holidays(_holidays)

  @classmethod
  def create(cls, date):
    r = req.post('/timesheet/', data={
      'newsheet': date.strftime('%m/%d/%Y'),
    }, referer='/accounts/login/')

    if 'That timesheet already exists' in r.text:
      click.echo(f'A timesheet already exists for {date_fmt(date)}', err=True)
      sys.exit(Error.TIMESHEET_EXISTS)

  @classmethod
  def latest(cls):
    timesheets = cls.list()
    if not timesheets:
      click.echo('No timesheets found', err=True)
      sys.exit(Error.TIMESHEET_MISSING)

    return list(timesheets.values())[0]

  @classmethod
  def from_user_date(cls, date):
    date = date_from_user_date(date)
    timesheet_date = find_sunday(date)

    timesheets = cls.list()
    if not timesheets:
      click.echo('No timesheets found', err=True)
      sys.exit(Error.TIMESHEET_MISSING)

    timesheet = timesheets.get(timesheet_date)
    if not timesheet:
      click.echo(f'No timesheet found for {date_fmt(timesheet_date)}', err=True)
      sys.exit(Error.TIMESHEET_MISSING)

    return timesheet

  @property
  def hours(self):
    return self._hours

  @property
  def items(self):
    if self._items is None:
      self._load_details()

    return self._items

  def submit(self):
    req.post(f'/timesheet/{self.id}/', data={
      'action': 'finalize',
    }, xhr=True)

  def _load_details(self):
    global _projects

    r = req.get(f'/timesheet/{self.id}/')
    doc = BeautifulSoup(r.text, 'html.parser')
    self._items = set()
    for row in doc.find('div', attrs={'class': 'tableholder'}).find_all('tr'):
      if not row.get('id'):
        continue

      self._items.add(TimesheetItem(
        id=row.find('input', attrs={'name': 'id'})['value'],
        hours=Decimal(row.find('input', attrs={'name': 'hours_worked'})['value']),
        date=datetime.strptime(row.find('input', attrs={'name': 'log_date'})['value'], '%m/%d/%Y').date(),
        project=row.find('select', attrs={'name': 'project'}).find('option', selected='selected').contents[0],
        description=row.find('textarea', attrs={'name': 'description'}).contents[0]
      ))

    _projects = {}
    for option in doc.find('select', id='fav_projects').find_all('option'):
      name = option.contents[0]
      _projects[name.lower()] = Project(
        option['value'],
        name,
        option.get('selected') == 'selected'
      )

  def add_item(self, date, project, hours, description, fill=False, merge=True):
    p = list_projects().get(project.lower())
    if not p:
      click.echo(f'Invalid project: {project}', err=True)
      sys.exit(Error.INVALID_ARGUMENT)

    try:
      hours = Decimal(hours)
    except InvalidOperation:
      click.echo(f'Invalid hours: {hours}', err=True)
      sys.exit(Error.INVALID_ARGUMENT)

    if -0.01 < hours < 0.01:
      click.echo('Hours cannot be 0', err=True)
      sys.exit(Error.INVALID_ARGUMENT)

    if hours < 0:
      click.echo(f'Hours cannot be negative: {hours}', err=True)
      sys.exit(Error.INVALID_ARGUMENT)

    if hours > 99.0:
      click.echo(f'Too many hours: {hours}', err=True)
      sys.exit(Error.INVALID_ARGUMENT)

    description = description.strip()
    if not description:
      click.echo('No description provided', err=True)
      sys.exit(Error.INVALID_ARGUMENT)

    if fill:
      current_hours = sum(i.hours for i in self.items if i.date == date)
      hours = min(hours, Decimal('8.0') - current_hours)
      if hours < 0.01:
        return

    to_delete = set()
    total_hours = hours
    if merge:
      for i in self.items:
        if all([i.date == date, i.project.lower() == project.lower(), i.description == description]):
          to_delete.add(i)
          total_hours += i.hours

    if total_hours > 99.0:
      click.echo(f'Merging this item with other items is too many hours: {total_hours}', err=True)
      click.echo('You can enter it as a separate item with the --no-merge flag', err=True)
      sys.exit(Error.INVALID_ARGUMENT)

    for i in to_delete:
      self.delete_item(i.id)

    req.post(f'/timesheet/{self.id}/', data={
      'log_date': date.strftime('%m/%d/%Y'),
      'project': p.id,
      'hours_worked': total_hours,
      'description': description,
      'ticket': '',
      'billing_type': 'M',
      'parent_ticket': '',
      'undefined': '',
    }, xhr=True)

  def delete_item(self, item_id):
    req.post(f'/timesheet/{self.id}/', data={
      'id': item_id,
      'action': 'delete',
    }, xhr=True)
