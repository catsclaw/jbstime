from pathlib import Path

import pytest
import requests_mock

from click.testing import CliRunner

from jbstime.client import cli


def response(r, method, url, filename=None, text=None):
  if filename:
    text = (Path(__file__).parent / 'html' / filename).read_text()

  getattr(r, method)(
    '//timetrack.jbecker.com' + url,
    text=text,
    cookies={'csrftoken': '**TOKEN**'}
  )


@pytest.fixture(scope='session', autouse=True)
def patch_urls():
  with requests_mock.mock() as r:
    response(r, 'get', '/', 'index.html')
    response(r, 'get', '/accounts/login/', 'login.html')
    response(r, 'get', '/timesheet/', 'timesheet.html')
    response(r, 'get', '/timesheet/27358/', '27358.html')

    response(r, 'post', '/accounts/login/', 'timesheet.html')
    response(r, 'post', '/timesheet/', 'timesheet.html')
    response(r, 'post', '/timesheet/27358/', text='Success')

    yield r


@pytest.fixture
def run():
  def _exec(*args):
    return CliRunner().invoke(cli, args)

  yield _exec
