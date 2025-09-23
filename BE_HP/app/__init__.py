from flask import Flask, jsonify
from flask_cors import CORS
from app.config import Config, SWAGGER_CONFIG, SWAGGER_TEMPLATE
from app.database import mongo
from flasgger import Swagger
from app.route import register_blueprints
from .extensions import get_db, init_indexes, jwt, limiter, socketio
from .error import register_error_handlers

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    CORS(app,
         supports_credentials=True,
         resources={r"/api/*": {"origins": [
            "http://localhost:4200",
     ]}})
    
    
    register_blueprints(app)
    jwt.init_app(app)
    limiter.init_app(app)
    mongo.init_app(app)
    socketio.init_app(app, cors_allowed_origins="http://localhost:4200")
    register_error_handlers(app)

    with app.app_context():
        db = get_db()
        init_indexes(db)

    for rule in app.url_map.iter_rules():
        print("ROUTE:", rule.endpoint, rule.rule, rule.methods)
    Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)

    return app