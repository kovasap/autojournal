from dataclasses import dataclass, field
from datetime import datetime, timedelta
from dateutil import tz

from . import calendar_api

@dataclass
class Event:
  timestamp: datetime
  summary: str
  description: str
  data: dict = field(default_factory=dict)
  duration: timedelta = timedelta(0)

  def to_calendar_event(self) -> calendar_api.CalendarEvent:
    return calendar_api.CalendarEvent(
      start=dict(
        dateTime=self.timestamp.replace(tzinfo=tz.gettz('PST')).isoformat(),
        timeZone='America/Los_Angeles'),
      end=dict(
        dateTime=(self.duration + self.timestamp).replace(
            tzinfo=tz.gettz('PST')).isoformat(),
        timeZone='America/Los_Angeles'),
      summary=self.summary,
      description=self.description,
    )
