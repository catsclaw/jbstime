class Timesheet:
  def __init__(self, id, date, hours, work_hours, locked):
    self.id = id
    self.date = date
    self.hours = hours
    self.work_hours = work_hours
    self.locked = locked
