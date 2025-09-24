from .extensions import socketio, TOKEN_BLOCKLIST
from flask import request
from flask_socketio import join_room, leave_room
from flask_jwt_extended import decode_token
from .require import load_user_for_role_check


@socketio.on("connect")
def handle_connect():
    print("Client connected", request.sid)

    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.args.get("token") or request.args.get("access_token")

    if not token:
        socketio.emit("auth_info", {"msg": "no token provided; connected as guest"}, room=request.sid)
        return

    try:
        decoded = decode_token(token)
    except Exception:
        socketio.emit("auth_error", {"msg": "invalid token"}, room=request.sid)
        return

    jti = decoded.get("jti")
    if jti and jti in TOKEN_BLOCKLIST:
        socketio.emit("auth_error", {"msg": "token revoked"}, room=request.sid)
        return

    identity = decoded.get("sub") or decoded.get("identity")
    if not identity:
        socketio.emit("auth_error", {"msg": "invalid token identity"}, room=request.sid)
        return

    user = load_user_for_role_check(identity)
    role = user.get("role_name") if user else None
    if role == "admin":
        join_room("admins")
        socketio.emit("auth_ok", {"role": "admin"}, room=request.sid)
        print(f"Socket {request.sid} authenticated as admin (user {identity})")
    else:
        socketio.emit("auth_ok", {"role": role}, room=request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected", request.sid)


@socketio.on("subscribe_logs")
def handle_subscribe_logs(data):
    room = None
    if isinstance(data, dict):
        room = data.get("room")
    if room:
        join_room(room)
        print(f"Client {request.sid} joined room {room}")
        socketio.emit("subscribed", {"room": room}, room=request.sid)
    else:
        # no room -> client will receive broadcasts
        socketio.emit("subscribed", {"room": None}, room=request.sid)


@socketio.on("authenticate")
def handle_authenticate(payload):
    token = None
    if isinstance(payload, dict):
        token = payload.get("access_token") or payload.get("token")
    if not token:
        socketio.emit("auth_error", {"msg": "missing token"}, room=request.sid)
        return

    try:
        decoded = decode_token(token)
    except Exception as e:
        socketio.emit("auth_error", {"msg": "invalid token"}, room=request.sid)
        return

    jti = decoded.get("jti")
    if jti and jti in TOKEN_BLOCKLIST:
        socketio.emit("auth_error", {"msg": "token revoked"}, room=request.sid)
        return

    identity = decoded.get("sub") or decoded.get("identity")
    if not identity:
        socketio.emit("auth_error", {"msg": "invalid token identity"}, room=request.sid)
        return

    user = load_user_for_role_check(identity)
    role = user.get("role_name") if user else None
    if role == "admin":
        join_room("admins")
        socketio.emit("auth_ok", {"role": "admin"}, room=request.sid)
        print(f"Socket {request.sid} authenticated as admin (user {identity})")
    else:
        socketio.emit("auth_ok", {"role": role}, room=request.sid)


@socketio.on("unsubscribe_logs")
def handle_unsubscribe_logs(data):
    room = None
    if isinstance(data, dict):
        room = data.get("room")
    if room:
        leave_room(room)
        print(f"Client {request.sid} left room {room}")
        socketio.emit("unsubscribed", {"room": room}, room=request.sid)
    else:
        socketio.emit("unsubscribed", {"room": None}, room=request.sid)
