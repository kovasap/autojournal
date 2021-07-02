from dataclasses import dataclass
from datetime import datetime
from dateutil import tz

from . import calendar_api

@dataclass
class Event:
  timestamp: datetime
  data: dict
  summary: str
  description: str

  def to_calendar_event(self) -> calendar_api.CalendarEvent:
    return calendar_api.CalendarEvent(
      start=dict(
        dateTime=self.timestamp.replace(tzinfo=tz.gettz('PST')).isoformat(),
        timeZone='America/Los_Angeles'),
      end=dict(
        dateTime=self.timestamp.replace(tzinfo=tz.gettz('PST')).isoformat(),
        timeZone='America/Los_Angeles'),
      summary=self.summary,
      description=self.description,
    )
