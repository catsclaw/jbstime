from datetime import datetime

from bs4 import BeautifulSoup

from . import req


class Timesheet:
  def __init__(self, id, date, hours, work_hours, locked):
    self.id = id
    self.date = date
    self.hours = hours
    self.work_hours = work_hours
    self.locked = locked

  @classmethod
  def list(cls):
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

    return dates
