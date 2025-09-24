
from flask import Flask, jsonify

class BadRequest(Exception): ...
class Unauthorized(Exception): ...
class Conflict(Exception): ...

def _err(payload: dict, status: int):
    return jsonify({"error": payload}), status

def register_error_handlers(app: Flask):
    @app.errorhandler(BadRequest)
    def _bad_request(e):
        return _err({"code": "BAD_REQUEST", "message": str(e)}, 400)

    @app.errorhandler(Unauthorized)
    def _unauthorized(e):
        return _err({"code": "UNAUTHORIZED", "message": str(e)}, 401)

    @app.errorhandler(Conflict)
    def _conflict(e):
        return _err({"code": "CONFLICT", "message": str(e)}, 409)

    @app.errorhandler(404)
    def _404(_):
        return _err({"code": "NOT_FOUND", "message": "Not found"}, 404)

    @app.errorhandler(500)
    def _500(e):
        return _err({"code": "INTERNAL", "message": "Internal Server Error"}, 500)
