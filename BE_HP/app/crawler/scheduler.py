import time
from datetime import datetime, timedelta
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
from ..extensions import get_db
from ..models.log_schemas import LogType
from ..routes.logs.log_utils import insert_log
from .meter_measurements_crawler import crawl_measurements_data
from .repair_data_crawler import crawl_repair_data

class CrawlerScheduler:
    def __init__(self):
        if SCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
        else:
            self.scheduler = None
        self.is_running = False
        self.app = None  # Sẽ được set từ bên ngoài
        
    def set_app(self, app):
        """Set Flask app instance để tạo context"""
        self.app = app
        
    def crawl_all_data_with_lock(self):
        """Wrapper method để tạo app context"""
        if self.app:
            with self.app.app_context():
                self._crawl_all_data_with_lock()
        else:
            # Fallback nếu không có app context
            self._crawl_all_data_with_lock()
    
    def _crawl_all_data_with_lock(self):
        """Method thực tế chạy crawl với lock"""
        db = get_db()
        lock_collection = db["scheduler_locks"]
        
        now = datetime.utcnow()
        expires = now + timedelta(hours=2)  
        
        try:
            result = lock_collection.find_one_and_update(
                {"job_name": "daily_crawl_job", "expires": {"$lt": now}},
                {"$set": {"locked_at": now, "expires": expires, "status": "running"}},
                upsert=True
            )
            
            if not result:
                try:
                    lock_collection.insert_one({
                        "job_name": "daily_crawl_job",
                        "locked_at": now,
                        "expires": expires,
                        "status": "running"
                    })
                except Exception:
                    insert_log("Một process khác đang chạy crawl job", LogType.INFO)
                    return
            
            self.perform_all_crawling()
            
    
            lock_collection.delete_one({"job_name": "daily_crawl_job"})
            
        except Exception as e:
            insert_log(f"Lỗi khi thực hiện crawl job: {str(e)}", LogType.ERROR)

            lock_collection.delete_one({"job_name": "daily_crawl_job"})
    
    def perform_all_crawling(self):
        start_time = time.time()
        
        try:
            crawl_measurements_data()
            crawl_repair_data()
        except Exception as e:
            insert_log(f"Lỗi khi thực hiện crawl tự động: {str(e)}", LogType.ERROR)
    
    def start_scheduler(self):
        if not SCHEDULER_AVAILABLE:
            insert_log("APScheduler không có sẵn. Không thể khởi động scheduler", LogType.ERROR)
            return
            
        if self.is_running:
            insert_log("Scheduler đã đang chạy", LogType.WARNING)
            return
        
        try:
            self.scheduler.add_job(
                self.crawl_all_data_with_lock,
                trigger=CronTrigger(hour=19, minute=00),
                id='daily_crawl_job',
                name='Crawl dữ liệu hàng ngày',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            insert_log("Đã khởi động scheduler crawl dữ liệu", LogType.INFO)
            
        except Exception as e:
            insert_log(f"Lỗi khi khởi động scheduler: {str(e)}", LogType.ERROR)
    
    def stop_scheduler(self):
      
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            insert_log("Đã dừng scheduler crawl dữ liệu", LogType.INFO)
    
    def get_next_run_time(self):
        if self.is_running:
            job = self.scheduler.get_job('daily_crawl_job')
            if job:
                return job.next_run_time
        return None

crawler_scheduler = CrawlerScheduler()