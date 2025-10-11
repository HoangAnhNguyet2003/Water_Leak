from flask import Flask
from flask_cors import CORS
import atexit
from app.config import Config, SWAGGER_CONFIG, SWAGGER_TEMPLATE
from app.database import mongo
from flasgger import Swagger
from app.route import register_blueprints
from .extensions import get_db, init_indexes, jwt, limiter, socketio
from .error import register_error_handlers
from .scheduler.app_scheduler import app_scheduler

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}})

    register_blueprints(app)
    jwt.init_app(app)
    limiter.init_app(app)
    mongo.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    register_error_handlers(app)

    with app.app_context():
        db = get_db()
        init_indexes(db)
        
        app_scheduler.set_app(app)
        
        try:
            app_scheduler.start_scheduler()
        except Exception as e:
            print(f"Không thể khởi động app scheduler: {e}")

    for rule in app.url_map.iter_rules():
        print("ROUTE:", rule.endpoint, rule.rule, rule.methods)
    Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)
    
    def shutdown_scheduler():
        try:
            app_scheduler.stop_scheduler()
        except Exception:
            pass
    atexit.register(shutdown_scheduler)

    return app