from dataclasses import dataclass
from datetime import datetime

@dataclass
class Event:
    timestamp: datetime
    data: dict

