from datetime import datetime, timedelta
from .crawler import api_client
from ..extensions import get_db
from ..models.log_schemas import LogType
from ..routes.logs.log_utils import insert_log
from ..utils.common import find_meterid_by_metername

def run_prediction_after_crawl():
    try:
        from ..ml.lstm_autoencoder.predict import LSTMAEPredictor
        from ..config import MLConfig
        
        
        predictor = LSTMAEPredictor(
            historical_context=MLConfig.HISTORICAL_DATA_DAYS,
            config=MLConfig.LSTM_AE_CONFIG,
            model_path=MLConfig.LSTM_AE_MODEL_PATH,
            debug=False  
        )
        
        result = predictor.predict()
        
        if result:
            total_data = result['total_data_points']
            today_data = result['today_data_points']
            predictions_count = result.get('predictions_count', 0)
            predictions_saved = result['predictions_saved']
            
            insert_log(
                f"Prediction hoàn tất: {total_data} historical data, {today_data} today data, "
                f"{predictions_count} predictions generated, {predictions_saved} predictions saved",
                LogType.INFO
            )
            
            if predictions_saved > 0:
                insert_log(f"Đã lưu {predictions_saved} predictions vào database", LogType.INFO)
            else:
                insert_log("Không có predictions mới để lưu", LogType.WARNING)
                
            return True
        else:
            insert_log("Prediction thất bại - không có kết quả trả về", LogType.ERROR)
            return False
            
    except Exception as e:
        insert_log(f"Lỗi khi chạy prediction: {str(e)}", LogType.ERROR)
        return False

def crawl_measurements_data(): 
    try: 
        start_date = datetime.now().strftime('%Y-%m-%d')
        time_range = "01:00-04:00"
        data = api_client.request(
            method="GET",
            endpoint="/api/scada/get_measurement_data_by_time",
            params={"start_date": start_date, "time_range": time_range},
            timeout=60
        )
        
        if data:
            insert_log(f"Đã crawl được {len(data)} bản ghi dữ liệu measurements", LogType.INFO)
            save_success = save_measurements_data(data)
            
            if save_success:
                insert_log("Bắt đầu chạy prediction sau khi crawl xong", LogType.INFO)
                run_prediction_after_crawl()
            else:
                insert_log("Bỏ qua prediction do lưu dữ liệu thất bại", LogType.WARNING)
                
            return data
        else:
            insert_log("Không có dữ liệu measurements mới", LogType.INFO)
            return []
        
    except Exception as e:
        insert_log(f"Lỗi khi crawl dữ liệu measurements: {str(e)}", LogType.ERROR)
        return None

def save_measurements_data(data):
    if not data:
        return False
    
    try:
        db = get_db()
        docs = []
        saved_count = 0
        error_count = 0
        
        for measurement in data:
            try:
                meter_name = measurement.get("meter_name")
                if not meter_name:
                    error_count += 1
                    continue
                
                meter_id = find_meterid_by_metername(meter_name)
                if not meter_id:
                    insert_log(f"Không tìm thấy meter với tên: {meter_name}", LogType.WARNING)
                    error_count += 1
                    continue
                
                measurement_time_str = measurement.get("measurement_time")
                if measurement_time_str:
                    try:
                        measurement_time = datetime.fromisoformat(measurement_time_str)
                    except ValueError as ve:
                        insert_log(f"Lỗi parse thời gian '{measurement_time_str}': {str(ve)}", LogType.ERROR)
                        error_count += 1
                        continue
                else:
                    error_count += 1
                    continue
                
                instant_flow = measurement.get("instant_flow")
                instant_pressure = measurement.get("pressure")
                
                if instant_flow == '' or instant_flow is None:
                    instant_flow = None
                else:
                    try:
                        instant_flow = float(instant_flow)
                    except (ValueError, TypeError):
                        instant_flow = None
                
                if instant_pressure == '' or instant_pressure is None:
                    instant_pressure = None
                else:
                    try:
                        instant_pressure = float(instant_pressure)
                    except (ValueError, TypeError):
                        instant_pressure = None
                
                doc = {
                    "meter_id": meter_id,
                    "measurement_time": measurement_time,
                    "instant_flow": instant_flow,
                    "instant_pressure": instant_pressure,
                }
                
                docs.append(doc)
                
            except Exception as e:
                insert_log(f"Lỗi khi xử lý bản ghi measurement: {str(e)}", LogType.ERROR)
                error_count += 1
                continue
        
        if docs:
            for doc in docs:
                db.meter_measurements.insert_one(doc)
                saved_count += 1
                
            insert_log(f"Đã lưu {saved_count} bản ghi measurements. Lỗi: {error_count}", LogType.INFO)
            return True
        else:
            insert_log(f"Không có bản ghi hợp lệ để lưu. Lỗi: {error_count}", LogType.WARNING)
            return False
            
    except Exception as e:
        insert_log(f"Lỗi khi lưu dữ liệu measurements: {str(e)}", LogType.ERROR)
        return False