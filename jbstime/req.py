import sys

import click
import requests

from . import config
from .error import Error


s = requests.Session()


def login():
  ctx = click.get_current_context(silent=True)
  info = ctx.obj if ctx else {}

  if info.get('logged_in'):
    return

  conf = config.load_config()

  username = info.get('cmd_username') or conf['username']
  password = info.get('cmd_password') or conf['password']

  if not username:
    username = click.prompt('Username')

  if not password:
    password = click.prompt('Password', hide_input=True)

  r = post('/accounts/login/', data={
    'username': username,
    'password': password,
  }, check_login=False)

  if 'Your username and password didn\'t match' in r.text:
    click.echo('Login failed. Check your username and password.', err=True)
    sys.exit(Error.LOGIN_FAILED)

  info['logged_in'] = True


def get(url, *args, check_login=True, **kw):
  if check_login:
    login()

  url = 'https://timetrack.jbecker.com' + url
  r = s.get(url, *args, **kw)
  r.raise_for_status()
  return r


def post(url, data, *args, referer=None, xhr=False, check_login=True, **kw):
  if check_login:
    login()

  referer = referer or url
  r = get(referer, check_login=check_login)
  csrf_token = r.cookies['csrftoken']

  data['csrf_token'] = csrf_token
  data['csrfmiddlewaretoken'] = csrf_token
  kw['headers'] = {
    'X-CSRFToken': csrf_token,
    'Referer': 'https://timetrack.jbecker.com' + referer,
  }

  if xhr:
    kw['headers']['X-Requested-With'] = 'XMLHttpRequest'

  url = 'https://timetrack.jbecker.com' + url
  r = s.post(url, *args, data=data, **kw)
  r.raise_for_status()
  return r
