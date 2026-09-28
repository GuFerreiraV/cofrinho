from datetime import date, datetime
from zoneinfo import ZoneInfo


def hoje(timezone: str) -> date:
    return datetime.now(ZoneInfo(timezone)).date()
