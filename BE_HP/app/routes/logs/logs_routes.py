from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from ...models.log_schemas import LogType
from .log_utils import get_logs, insert_log
from ...require import require_role
from ...utils import get_swagger_path, find_by_id
from flasgger import swag_from

logs_bp = Blueprint("logs", __name__)


@logs_bp.route('/get_all_logs', methods=['GET'])
@jwt_required()
@require_role('admin')
@swag_from(get_swagger_path('logs/get_all.yml'))
def list_logs():
	logs = get_logs()
	result = []

	for l in logs:
		time_ = l.create_time if l.create_time else None
		if time_: 
			time_ = time_.strftime("%Y-%m-%d %H:%M")
		result.append({
            "id": str(getattr(l, 'id', None)) if getattr(l, 'id', None) else None,
            "source": l.source,
            "create_time": time_, 
            "log_type": int(l.log_type) if l.log_type is not None else None,
            "message": l.message,
        })
	return jsonify(result), 200
