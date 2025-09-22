from datetime import datetime
from typing import Optional
from bson import ObjectId
from ...extensions import get_db
from ...utils.bson import to_object_id, oid_str

COL = "predictions"


def count_distinct_leak_meters_in_day(start_utc: datetime,
                                      end_utc: datetime,
                                      branch_id: Optional[ObjectId] = None) -> int:
    """
    Đếm số đồng hồ bị rò rỉ trong NGÀY (distinct theo meter_id).
    Nếu branch_id != None: chỉ tính trong chi nhánh đó.
    """
    db = get_db()
    match_stage = {
        "predicted_label": "leak",
        "prediction_time": {"$gte": start_utc, "$lt": end_utc},
    }

    pipeline = [{"$match": match_stage}]

    # Nếu cần giới hạn theo chi nhánh, join sang meters để lọc branch
    if branch_id:
        pipeline += [
            {"$lookup": {
                "from": "meters",
                "localField": "meter_id",
                "foreignField": "_id",
                "as": "m"
            }},
            {"$unwind": "$m"},
            {"$match": {"m.branch_id": branch_id}},
        ]

    pipeline += [
        {"$group": {"_id": "$meter_id"}},  # distinct meter_id
        {"$count": "leak_meters"}
    ]

    doc = list(db[COL].aggregate(pipeline))
    return int(doc[0]["leak_meters"]) if doc else 0