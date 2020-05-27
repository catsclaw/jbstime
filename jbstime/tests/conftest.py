import pathlib
from unittest.mock import patch

from click.testing import CliRunner
import pytest
import requests_mock

from jbstime.api import _clear
from jbstime.client import cli


@pytest.fixture(scope='session', autouse=True)
def urls():
  with requests_mock.mock() as r:
    def response(method, url, filename=None, text=None, post=None):
      if filename:
        path = pathlib.Path(__file__).parent / 'html' / filename
        text = path.read_text()

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

    response('get', '/', 'index.html')
    response('get', '/accounts/login/', 'login.html')
    response('get', '/timesheet/', 'timesheet.html')
    response('get', '/timesheet/27358/', '27358.html')
    response('get', '/timesheet/27299/', '27358.html')

    response('post', '/accounts/login/', 'timesheet.html')
    response('post', '/accounts/login/', text='Your username and password didn\'t match', post='username=baduser')
    response('post', '/timesheet/', 'timesheet.html', post='newsheet=05%2F24%2F2020')
    response('post', '/timesheet/', text='That timesheet already exists', post='newsheet=05%2F10%2F2020')
    response('post', '/timesheet/27358/', text='Success')

    yield r


@pytest.fixture(autouse=True)
def config(fs):
  with patch.dict('os.environ', {
    'JBS_TIMETRACK_USER': 'user',
    'JBS_TIMETRACK_PASS': 'pass',
  }):
    yield


@pytest.fixture()
def no_config(fs):
  with patch.dict('os.environ', {
    'JBS_TIMETRACK_USER': '',
    'JBS_TIMETRACK_PASS': '',
  }):
     yield


@pytest.fixture()
def run():
  def _exec(*args, input=None):
    _clear()
    return CliRunner().invoke(cli, args, input=input)

  yield _exec
