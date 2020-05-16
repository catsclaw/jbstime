from collections import namedtuple
from datetime import datetime

from bs4 import BeautifulSoup
import click

from . import req
from .dates import date_fmt, date_from_user_date, find_sunday


_timesheets = None
_projects = None


TimesheetItem = namedtuple('TimesheetItem', 'id hours date project description')
Project = namedtuple('Project', 'id name favorite')


class Timesheet:
  def __init__(self, id, date, hours, work_hours, locked):
    self.id = id
    self.date = date
    self.hours = hours
    self.work_hours = work_hours
    self.locked = locked

    self._items = None

  @classmethod
  def list(cls):
    global _timesheets
    if _timesheets:
      return _timesheets

    r = req.get('/?all=1')

    doc = BeautifulSoup(r.text, 'html.parser')
    dates = {}
    for row in doc.find('table', attrs={'class': 'latest-timesheet-table'}).find_all('tr'):
      data = row.find_all('td')
      if not data:
        continue

      timesheet_date = datetime.strptime(data[1].contents[0][12:], '%m/%d/%Y').date()
      dates[timesheet_date] = Timesheet(
        data[5].find('a')['href'][11:-1],
        timesheet_date,
        float(data[2].contents[0]),
        float(data[3].contents[0]),
        (data[0].find('span')['class'] + [None])[0]  == 'locked',
      )

    _timesheets = dates
    return _timesheets

  @classmethod
  def create(cls):
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
  def projects(cls):
    latest = cls.latest()
    latest.items  # Ensures the projects are loaded
    return _projects

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
  def items(self):
    if self._items is None:
      self._load_details()

    return self._items

  def _load_details(self):
    global _projects

    r = req.get(f'/timesheet/{self.id}/')

    doc = BeautifulSoup(r.text, 'html.parser')
    self._items = set()
    for row in doc.find('div', attrs={'class': 'tableholder'}).find_all('tr'):
      if not row.get('id'):
        continue

      self._items.add(TimesheetItem(
        row.find('input', attrs={'name': 'id'})['value'],
        float(row.find('input', attrs={'name': 'hours_worked'})['value']),
        datetime.strptime(row.find('input', attrs={'name': 'log_date'})['value'], '%m/%d/%Y').date(),
        row.find('select', attrs={'name': 'project'}).find('option', selected='selected').contents[0],
        row.find('textarea', attrs={'name': 'description'}).contents[0]
      ))

    _projects = {}
    for option in doc.find('select', id='fav_projects').find_all('option'):
      name = option.contents[0]
      _projects[name.lower()] = Project(
        option['value'],
        name,
        option.get('selected') == 'selected'
      )
