from flask import Blueprint 
from .routes.auth.auth_routes import auth_bp
from .routes.users.user_routes import user_bp
from .routes.meter.meter_routes import meter_bp
from .routes.branches.branch_routes import branch_bp
from .routes.measurements.measurements_routes import m_bp
from .routes.predictions.predictions_routes import pred_bp
from .routes.logs.logs_routes import logs_bp
from .routes.repair.repair_routes import repair_bp
from .routes.crawler.crawler_routes import crawler_bp

main_bp = Blueprint('main', __name__)

def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(user_bp, url_prefix='/api/v1/users')
    app.register_blueprint(meter_bp, url_prefix='/api/v1/meters')
    app.register_blueprint(branch_bp, url_prefix='/api/v1/branches')
    app.register_blueprint(m_bp, url_prefix='/api/v1/measurements')
    app.register_blueprint(pred_bp, url_prefix='/api/v1/predictions')
    app.register_blueprint(logs_bp, url_prefix='/api/v1/logs')
    app.register_blueprint(repair_bp, url_prefix='/api/v1/repairs')
    app.register_blueprint(crawler_bp, url_prefix='/api/v1/crawler')