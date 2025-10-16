from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

ASIA_HCM_OFFSET = 7

VIETNAM_TZ = timezone(timedelta(hours=ASIA_HCM_OFFSET))

def get_vietnam_now():
    return datetime.now(VIETNAM_TZ)

def day_bounds_utc(date_str: Optional[str]) -> Tuple[str, datetime, datetime]:

    if date_str:
        local_day = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        now_local = get_vietnam_now()
        local_day = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    start_local = local_day.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=VIETNAM_TZ)
    end_local   = start_local + timedelta(days=1)

    return start_local.strftime("%Y-%m-%d"), start_local, end_local