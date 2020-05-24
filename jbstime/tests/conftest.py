from pathlib import Path
from unittest.mock import patch

import pytest
import requests_mock

from click.testing import CliRunner

from jbstime.client import cli


def response(r, method, url, filename=None, text=None, post=None):
  if filename:
    text = (Path(__file__).parent / 'html' / filename).read_text()

  if post:
    def matcher(r):
      return post in r.body
  else:
    matcher = None

  getattr(r, method)(
    '//timetrack.jbecker.com' + url,
    text=text,
    cookies={'csrftoken': '**TOKEN**'},
    additional_matcher=matcher,
  )


@pytest.fixture(scope='session', autouse=True)
def urls():
  with requests_mock.mock() as r:
    response(r, 'get', '/', 'index.html')
    response(r, 'get', '/accounts/login/', 'login.html')
    response(r, 'get', '/timesheet/', 'timesheet.html')
    response(r, 'get', '/timesheet/27358/', '27358.html')
    response(r, 'get', '/timesheet/27299/', '27358.html')

    response(r, 'post', '/accounts/login/', 'timesheet.html')
    response(r, 'post', '/accounts/login/', text='Your username and password didn\'t match', post='username=baduser')
    response(r, 'post', '/timesheet/', 'timesheet.html', post='newsheet=05%2F24%2F2020')
    response(r, 'post', '/timesheet/', text='That timesheet already exists', post='newsheet=05%2F10%2F2020')
    response(r, 'post', '/timesheet/27358/', text='Success')

    yield r


@pytest.fixture(scope='session', autouse=True)
def config():
  with patch.dict('os.environ', {
    'JBS_TIMETRACK_USER': 'user',
    'JBS_TIMETRACK_PASS': 'pass',
  }):
    yield


@pytest.fixture
def run():
  def _exec(*args, input=None):
    return CliRunner().invoke(cli, args, input=input)

  yield _exec
