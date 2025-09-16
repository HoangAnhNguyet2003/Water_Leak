
from flask import jsonify, make_response

def json_ok(payload, status: int = 200, headers: dict | None = None):
    resp = make_response(jsonify(payload), status)
    resp.headers.setdefault("Content-Type", "application/json; charset=utf-8")
    if headers:
        for k, v in headers.items():
            resp.headers[k] = v
    return resp

def created(resource_path: str, body: dict):
    return json_ok(body, 201, headers={"Location": resource_path})

def no_content():
    return ("", 204)
