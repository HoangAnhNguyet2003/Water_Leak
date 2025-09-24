from functools import wraps
from typing import Callable
from flask import request
from flask_jwt_extended import get_jwt_identity

try:
    # newer versions provide an optional verify helper
    from flask_jwt_extended import verify_jwt_in_request_optional
except Exception:
    verify_jwt_in_request_optional = None

from ..routes.logs.log_utils import insert_log
from ..models.log_schemas import LogType



def _get_current_user_id_optional():
    try:
        if verify_jwt_in_request_optional is not None:
            verify_jwt_in_request_optional()
        else:
            pass
        return get_jwt_identity()
    except Exception:
        return None


def log_api(log_type: LogType = LogType.INFO, message: str | None = None) -> Callable:
    """
    Usage:
      @app.route(...)
      @log_api(LogType.INFO, "User created meter")
      def create_meter():
          ...
    """
    def deco(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Prepare a friendly message
            try:
                user_id = _get_current_user_id_optional()
                status_code = None
                if isinstance(result, tuple) and len(result) >= 2 and isinstance(result[1], int):
                    status_code = result[1]
                else:
                    try:
                        status_code = getattr(result, "status_code", None)
                    except Exception:
                        status_code = None

                msg = message or f"{request.method} {request.path}"
                if status_code is not None:
                    msg = f"{msg}"

                insert_log(message=msg, log_type=log_type, user_id=user_id)
            except Exception:
                pass

            return result

        return wrapper

    return deco
