import requests


s = requests.Session()


def get(url, *args, **kw):
  url = 'https://timetrack.jbecker.com' + url
  r = s.get(url, *args, **kw)
  r.raise_for_status()
  return r


def post(url, data, *args, referer=None, xhr=False, **kw):
  referer = referer or url
  r = get(referer)
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
