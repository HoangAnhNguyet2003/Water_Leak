from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from flasgger import swag_from
from ...require import require_role
from ...models.log_schemas import LogType
from ...routes.logs.log_utils import insert_log
from ...utils import get_swagger_path
from ...crawler.meter_measurements_crawler import crawl_measurements_data
from ...crawler.repair_data_crawler import crawl_repair_data
import threading
from flask import current_app

crawler_bp = Blueprint("crawler", __name__)

@crawler_bp.post("/test/all")
@jwt_required(optional=False, verify_type=False)
@swag_from(get_swagger_path('crawler/test_all.yml'))
@require_role("admin")
def test_all_crawling():
    """Test crawl tất cả dữ liệu"""
    try:
        app = current_app._get_current_object()  # Lấy app instance
        
        def run_job():
            with app.app_context():
                try:
                    insert_log("Bắt đầu crawl trong thread", LogType.INFO)
                    measurements_result = crawl_measurements_data()
                    insert_log(f"Crawl measurements hoàn thành", LogType.INFO)
                    
                    repairs_result = crawl_repair_data()
                    insert_log(f"Crawl repairs hoàn thành", LogType.INFO)
                    
                    insert_log("Hoàn thành tất cả crawl jobs", LogType.INFO)
                except Exception as e:
                    insert_log(f"Lỗi trong thread crawl: {str(e)}", LogType.ERROR)
                
        thread = threading.Thread(target=run_job)
        thread.daemon = True
        thread.start()
        
        insert_log("Đã kích hoạt test crawl tất cả dữ liệu", LogType.INFO)
        return jsonify({"message": "Đã kích hoạt test crawl tất cả dữ liệu"}), 200
    except Exception as e:
        insert_log(f"Lỗi khi test crawl all: {str(e)}", LogType.ERROR)
        return jsonify({"error": str(e)}), 500