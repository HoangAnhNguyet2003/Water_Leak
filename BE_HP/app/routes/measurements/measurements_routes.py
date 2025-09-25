from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from ...require import require_role
from .measurement_utils import get_latest_flow, get_daily_flow
from ...utils import get_swagger_path
from flasgger import swag_from
from ...extensions import get_db
from ...utils import to_object_id
from datetime import datetime, timedelta, timezone

m_bp = Blueprint("measurements", __name__)

@m_bp.get("/<mid>/instant-flow")
@swag_from(get_swagger_path('measurements/instant_flow.yml'))
@jwt_required()
@require_role("branch_manager", "company_manager", "admin")
def latest_instant_flow(mid):
    print(f"Fetching latest instant flow for meter {mid}...")
    data = get_latest_flow(mid)
    return jsonify(data), 200

@m_bp.get("/<mid>/instant-flow/daily")
@swag_from(get_swagger_path('measurements/daily_instant_flow.yml'))
@jwt_required()
@require_role("branch_manager", "company_manager", "admin")
def daily_instant_flow(mid):
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Missing query param 'date' (YYYY-MM-DD)"}), 400
    data = get_daily_flow(mid, date_str)
    return jsonify(data), 200


@m_bp.get("/<mid>/range")
@swag_from(get_swagger_path('measurements/range.yml'))
@jwt_required()
@require_role("branch_manager", "company_manager", "admin")
def measurements_range(mid):
    try:
        hours = int(request.args.get('hours', 4))
    except Exception:
        return jsonify({"error": "Invalid 'hours' parameter"}), 400

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(hours=hours)

    db = get_db()
    try:
        docs = list(db.meter_measurements.find({
            "meter_id": to_object_id(mid),
            "measurement_time": {"$gte": start_dt, "$lte": end_dt}
        }).sort("measurement_time", 1))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Format timestamps as 'dd-mm-yyyy - H'
    def fmt(dt):
        return dt.strftime('%d-%m-%Y - %H')

    response = {
        "meter_id": mid,
        "start": fmt(start_dt),
        "end": fmt(end_dt),
        "items": [
            {
                "timestamp": fmt(d.get('measurement_time')),
                "flow": d.get('instant_flow')
            } for d in docs
        ]
    }
    return jsonify(response), 200


@m_bp.get("/<mid>/range_with_predictions")
@swag_from(get_swagger_path('measurements/range_with_predictions.yml'))
@jwt_required()
@require_role("branch_manager", "company_manager", "admin")
def measurements_range_with_predictions(mid):
    try:
        hours = int(request.args.get('hours', 4))
    except Exception:
        return jsonify({"error": "Invalid 'hours' parameter"}), 400

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(hours=hours)

    db = get_db()
    try:
        docs = list(db.meter_measurements.find({
            "meter_id": to_object_id(mid),
            "measurement_time": {"$gte": start_dt, "$lte": end_dt}
        }).sort("measurement_time", 1))

        preds_cursor = db.predictions.find({
            "meter_id": to_object_id(mid),
            "prediction_time": {"$gte": start_dt, "$lte": end_dt}
        })
        preds = [p for p in preds_cursor]
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    def fmt(dt):
        return dt.strftime('%d-%m-%Y - %H')

    pred_map = {}
    for p in preds:
        pt = p.get('prediction_time')
        if not pt:
            continue
        key = fmt(pt)
        existing = pred_map.get(key)
        if not existing or (p.get('confidence', 0) > existing.get('confidence', 0)):
            pred_map[key] = p

    items = []
    for d in docs:
        ts = fmt(d.get('measurement_time'))
        base = {
            "timestamp": ts,
            "flow": d.get('instant_flow')
        }
        p = pred_map.get(ts)
        if p:
            predicted_flow = p.get('predicted_flow') if 'predicted_flow' in p else p.get('flow')
            is_anom = bool(p.get('is_anomaly', False))
            conf = float(p.get('confidence', 0) or 0)
            status = 'anomaly' if is_anom else 'normal'
        else:
            predicted_flow = None
            is_anom = False
            conf = 0.0
            status = 'normal'

        base.update({
            "predicted_flow": predicted_flow,
            "is_anomaly": is_anom,
            "confidence": conf,
            "status": status
        })
        items.append(base)

    response = {
        "meter_id": mid,
        "start": fmt(start_dt),
        "end": fmt(end_dt),
        "items": items
    }
    return jsonify(response), 200

