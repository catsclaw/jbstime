from datetime import datetime, timedelta
import sys

from dateutil.parser import parse
from dateutil.parser._parser import ParserError

from .error import Error


def date_fmt(d):
  return f'{d:%b} {d.day}, {d.year}'


def date_fmt_pad_day(d):
  return f'{d:%b} {d.day:>2}, {d.year}'


def date_from_user_date(date):
  if date == 'today':
    return datetime.now().date()

  try:
    date = parse(date).date()
  except ParserError:
    click.echo(f'Can\'t parse date: {data[0]}', err=True)
    sys.exit(Error.UNPARSABLE_DATE)

  return date


def find_sunday(d):
  return d + timedelta(days=(6 - d.weekday()))
