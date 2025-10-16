import time
import threading
from datetime import datetime, timedelta, timezone
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
from ..extensions import get_db
from ..utils import get_vietnam_now, VIETNAM_TZ
from ..models.log_schemas import LogType
from ..routes.logs.log_utils import insert_log
from ..crawler.meter_measurements_crawler import crawl_measurements_data
from ..crawler.repair_data_crawler import crawl_repair_data
from ..routes.meter.meter_utils import create_daily_thresholds_for_all_meters

class AppScheduler:
    def __init__(self):
        if SCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
        else:
            self.scheduler = None
        self.is_running = False
        self.app = None 
        
    def set_app(self, app):
        self.app = app
        
    def crawl_all_data_with_lock(self):
        if self.app:
            with self.app.app_context():
                self._crawl_all_data_with_lock()
        else:
            self._crawl_all_data_with_lock()
    
    def _crawl_all_data_with_lock(self):
        db = get_db()
        lock_collection = db["scheduler_locks"]
        
        now = get_vietnam_now()
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
            
            self._execute_crawling_sequence()
            insert_log("Scheduled crawl hoàn thành", LogType.INFO)
            
            lock_collection.delete_one({"job_name": "daily_crawl_job"})
            
        except Exception as e:
            insert_log(f"Lỗi khi thực hiện crawl job: {str(e)}", LogType.ERROR)
            lock_collection.delete_one({"job_name": "daily_crawl_job"})
    
    def _execute_crawling_sequence(self):
        try:            
            if not self._check_api_health():
                insert_log("API health check failed, skip crawling", LogType.WARNING)
                return
            
            measurements_result = crawl_measurements_data()
            insert_log(f"Scheduled crawl measurements hoàn thành", LogType.INFO)
            
            repairs_result = crawl_repair_data() 
            insert_log(f"Scheduled crawl repairs hoàn thành", LogType.INFO)
                        
        except Exception as e:
            insert_log(f"Lỗi trong scheduled crawling sequence: {str(e)}", LogType.ERROR)
            raise
    
    def _check_api_health(self):
        try:
            import requests
            import os
            
            base_url = os.getenv('DATA_API_URL', 'https://dhxdapi.capnuochaiphong.com.vn')
            
            login_url = f"{base_url}/api/user/login"
            response = requests.head(login_url, timeout=10)
            
            if response.status_code in [200, 400, 401, 405]:
                insert_log(f"API health check passed: {response.status_code} in {response.elapsed.total_seconds()*1000:.0f}ms", LogType.INFO)
                return True
            else:
                insert_log(f"API health check failed: status {response.status_code}", LogType.WARNING)
                return False
                
        except requests.exceptions.Timeout:
            insert_log("API health check timeout - API may be slow", LogType.WARNING)
            return False
        except requests.exceptions.ConnectionError:
            insert_log("API health check connection error - API may be down", LogType.ERROR)  
            return False
        except Exception as e:
            insert_log(f"API health check error: {str(e)}", LogType.WARNING)
            return False
    
    def create_daily_thresholds_with_lock(self):
        if self.app:
            with self.app.app_context():
                self._create_daily_thresholds_with_lock()
        else:
            self._create_daily_thresholds_with_lock()
    
    def _create_daily_thresholds_with_lock(self):
        db = get_db()
        lock_collection = db["scheduler_locks"]
        
        now = get_vietnam_now()
        expires = now + timedelta(hours=1)
        
        try:
            result = lock_collection.find_one_and_update(
                {"job_name": "daily_threshold_job", "expires": {"$lt": now}},
                {"$set": {"locked_at": now, "expires": expires, "status": "running"}},
                upsert=True
            )
            
            if not result:
                try:
                    lock_collection.insert_one({
                        "job_name": "daily_threshold_job",
                        "locked_at": now,
                        "expires": expires,
                        "status": "running"
                    })
                except Exception:
                    insert_log("Một process khác đang chạy threshold job", LogType.INFO)
                    return
            
            try:
                result = create_daily_thresholds_for_all_meters()
                insert_log(f"Đã tạo threshold tự động: {result['success_count']} thành công, {result['error_count']} lỗi", LogType.INFO)
            except Exception as e:
                insert_log(f"Lỗi khi tạo threshold tự động: {str(e)}", LogType.ERROR)
            
            lock_collection.delete_one({"job_name": "daily_threshold_job"})
            
        except Exception as e:
            insert_log(f"Lỗi khi thực hiện threshold job: {str(e)}", LogType.ERROR)
            lock_collection.delete_one({"job_name": "daily_threshold_job"})
    
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
                trigger=CronTrigger(hour=5, minute=30),
                id='daily_crawl_job',
                name=f'Crawl dữ liệu hàng ngày',
                replace_existing=True
            )
            
            self.scheduler.add_job(
                self.create_daily_thresholds_with_lock,
                trigger=CronTrigger(hour=23, minute=50),
                id='daily_threshold_job',
                name='Tạo threshold hàng ngày',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            insert_log("Đã khởi động scheduler với crawl job (6:30 AM) và threshold job (23:50)", LogType.INFO)
            
        except Exception as e:
            insert_log(f"Lỗi khi khởi động scheduler: {str(e)}", LogType.ERROR)
    
    def stop_scheduler(self):
      
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            insert_log("Đã dừng scheduler", LogType.INFO)
    
    def get_next_run_time(self):
        if self.is_running:
            job = self.scheduler.get_job('daily_crawl_job')
            if job:
                return job.next_run_time
        return None
    
    def get_threshold_next_run_time(self):
        if self.is_running:
            job = self.scheduler.get_job('daily_threshold_job')
            if job:
                return job.next_run_time
        return None
    
    def get_all_jobs_info(self):
        jobs_info = []
        if self.is_running:
            for job in self.scheduler.get_jobs():
                jobs_info.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
        return jobs_info

app_scheduler = AppScheduler()