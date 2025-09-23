from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

ASIA_HCM_OFFSET = 7

def day_bounds_utc(date_str: Optional[str]) -> Tuple[str, datetime, datetime]:
    """
    Trả về (YYYY-MM-DD theo VN, start_utc, end_utc) cho ngày đó.
    """
    if date_str:
        local_day = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc + timedelta(hours=ASIA_HCM_OFFSET)
        local_day = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    start_local = local_day.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local   = start_local + timedelta(days=1)

    start_utc = (start_local - timedelta(hours=ASIA_HCM_OFFSET)).replace(tzinfo=timezone.utc)
    end_utc   = (end_local   - timedelta(hours=ASIA_HCM_OFFSET)).replace(tzinfo=timezone.utc)
    return start_local.strftime("%Y-%m-%d"), start_utc, end_utc