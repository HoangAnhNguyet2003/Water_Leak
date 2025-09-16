
from flask import Flask
from .config import get_config
from .extensions import get_db, init_indexes, close_db, jwt, limiter
from .api import api_v1
from .errors import register_error_handlers
from flask_cors import CORS

def create_app(env: str = "dev") -> Flask:
    print("Environment:", env)
    print("Starting app...")
    app = Flask(__name__)
    app.config.from_object(get_config(env))

    # Configure CORS to support credentials (cookies)
    CORS(app,
     supports_credentials=True,
     resources={r"/api/*": {"origins": [
         "http://localhost:4200",
         "http://localhost:4201",
         "http://localhost:4202"
     ]}})
    
    
    app.register_blueprint(api_v1)
    jwt.init_app(app)
    limiter.init_app(app)
    register_error_handlers(app)

    with app.app_context():
        list_routes(app)
        db = get_db()
        init_indexes(db)
    

    app.teardown_appcontext(close_db)
    return app

def list_routes(app: Flask):
    print("Registered routes:")
    output = []
    for rule in app.url_map.iter_rules():
        methods = ",".join(sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS")))
        line = f"{rule.endpoint:30s} {methods:15s} -> {rule.rule}"
        output.append(line)
    for line in sorted(output):
        print(line)