from datetime import datetime, timedelta
import time
from .crawler import api_client
from ..extensions import get_db
from ..models.log_schemas import LogType
from ..routes.logs.log_utils import insert_log
from ..utils.common import find_meterid_by_metername

def crawl_repair_data(): 
    max_retries = 3
    retry_delays = [60, 120, 300]  # 1 phút, 2 phút, 5 phút
    
    # Đảm bảo token fresh trước khi bắt đầu crawl
    insert_log("Kiểm tra và refresh token trước khi crawl repair data", LogType.INFO)
    if not api_client.ensure_token():
        insert_log("Không thể lấy token để crawl repair data", LogType.ERROR)
        return None
    
    for attempt in range(max_retries):
        try: 
            insert_log(f"Thử crawl repair data lần {attempt + 1}/{max_retries}", LogType.INFO)
            
            start_date = datetime.now().strftime('%Y-%m-%d')
            
            data = api_client.request(
                method="GET",
                endpoint="/api/git/get_all_repair",
                params={"start_date": start_date},
                timeout=90  # Tăng timeout lên 90s
            )
            
            if data:
                insert_log(f"Đã crawl được {len(data)} bản ghi dữ liệu sửa chữa", LogType.INFO)
                save_repair_data(data)
                return data
            else:
                insert_log("Không có dữ liệu sửa chữa mới", LogType.INFO)
                return []
                
        except Exception as e:
            error_msg = str(e)
            insert_log(f"Lần thử {attempt + 1} thất bại: {error_msg}", LogType.WARNING)
            
            if attempt < max_retries - 1:
                delay = retry_delays[attempt]
                insert_log(f"Đợi {delay}s trước khi thử lại...", LogType.INFO)
                time.sleep(delay)
            else:
                insert_log(f"Đã thử {max_retries} lần và thất bại. Lỗi cuối: {error_msg}", LogType.ERROR)
                if "400" in error_msg and "Bad Request" in error_msg:
                    try:
                        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                        insert_log(f"Thử test crawl repair với ngày hôm qua: {yesterday} (không lưu DB)", LogType.INFO)
                        
                        test_data = api_client.request(
                            method="GET",
                            endpoint="/api/git/get_all_repair",
                            params={"start_date": yesterday},
                            timeout=90
                        )
                        
                        if test_data:
                            insert_log(f"Test crawl repair với ngày hôm qua thành công: {len(test_data)} bản ghi (chỉ log, không lưu DB)", LogType.INFO)
                        else:
                            insert_log("Test crawl repair với ngày hôm qua không có dữ liệu", LogType.WARNING)
                            
                    except Exception as e2:
                        insert_log(f"Test crawl repair với ngày hôm qua thất bại: {str(e2)}", LogType.ERROR)
                
                return None
    
    return None

def save_repair_data(data):
    """Lưu dữ liệu repair vào database dựa trên logic seed_meter_repairs"""
    if not data:
        insert_log("Không có dữ liệu repair để lưu", LogType.WARNING)
        return False
    
    try:
        db = get_db()
        docs = []
        saved_count = 0
        error_count = 0
        
        for repair in data:
            try:
                meter_name = repair.get("meter_name")
                if not meter_name:
                    error_count += 1
                    continue
                
                meter_id = find_meterid_by_metername(meter_name)
                if not meter_id:
                    insert_log(f"Không tìm thấy meter với tên: {meter_name}", LogType.WARNING)
                    error_count += 1
                    continue
                
                recorded_time_str = repair.get("recorded_time")
                recorded_time = None
                if recorded_time_str and recorded_time_str != '':
                    try:
                        recorded_time = datetime.fromisoformat(recorded_time_str)
                    except ValueError:
                        insert_log(f"Lỗi parse recorded_time '{recorded_time_str}'", LogType.WARNING)
                
                repair_time_str = repair.get("repair_time")
                repair_time = None
                if repair_time_str and repair_time_str != '':
                    try:
                        repair_time = datetime.fromisoformat(repair_time_str)
                    except ValueError:
                        insert_log(f"Lỗi parse repair_time '{repair_time_str}'", LogType.WARNING)
                

                leak_reason = repair.get("leak_reason")
                if not leak_reason or leak_reason == '':
                    leak_reason = "Unknown"
                
                replacement_type = repair.get("replacement_type")
                if not replacement_type or replacement_type == '':
                    replacement_type = "Not specified"
                
                replacement_location = repair.get("replacement_location")
                if not replacement_location or replacement_location == '':
                    replacement_location = "Not specified"
                
       
                doc = {
                    "meter_id": meter_id,
                    "recorded_time": recorded_time,
                    "repair_time": repair_time,
                    "leak_reason": leak_reason,
                    "replacement_type": replacement_type,
                    "replacement_location": replacement_location,
                }
                
                docs.append(doc)
                
            except Exception as e:
                insert_log(f"Lỗi khi xử lý bản ghi repair: {str(e)}", LogType.ERROR)
                error_count += 1
                continue
        
  
        if docs:
           
            for doc in docs:
                
                db.meter_repairs.insert_one(doc)
                saved_count += 1
            
            insert_log(f"Đã lưu/cập nhật bản ghi repair. Lỗi: {error_count}", LogType.INFO)
            return True
        else:
            insert_log(f"Không có bản ghi hợp lệ để lưu. Lỗi: {error_count}", LogType.WARNING)
            return False
            
    except Exception as e:
        insert_log(f"Lỗi khi lưu dữ liệu repair: {str(e)}", LogType.ERROR)
        return False
