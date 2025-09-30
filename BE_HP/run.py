from app import create_app
from app.extensions import socketio
from scripts.seed_data import main
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
import sys
import os

app = create_app()

if __name__ == "__main__":
    main()

    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))

    print(f"Starting server on {host}:{port}")
    server = pywsgi.WSGIServer(
        (host, port),
        app,
        handler_class=WebSocketHandler,
        log=sys.stdout
    )
    server.serve_forever()
