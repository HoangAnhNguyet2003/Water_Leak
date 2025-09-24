from app import create_app
from app.extensions import socketio
from scripts.seed_data import main
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
import sys 

app = create_app()

if __name__ == "__main__":
    main()
    server = pywsgi.WSGIServer(
        ("0.0.0.0", 5000),
        app,
        handler_class=WebSocketHandler,
        log=sys.stdout
    )
    server.serve_forever()
