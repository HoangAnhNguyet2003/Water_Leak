from datetime import datetime, timedelta
import time
import os
from .crawler import api_client
from ..extensions import get_db
from ..models.log_schemas import LogType
from ..routes.logs.log_utils import insert_log
from ..utils.common import find_meterid_by_metername

def run_lstmae_prediction_after_crawl(target_date=None):
    try:
        from ..ml.lstm_autoencoder.predict import LSTMAEPredictor
        from ..config import MLConfig
        
        
        predictor = LSTMAEPredictor(
            historical_context=MLConfig.HISTORICAL_DATA_DAYS,
            config=MLConfig.LSTM_AE_CONFIG,
            model_path=MLConfig.LSTM_AE_MODEL_PATH,
            debug=False  
        )
        
        result = predictor.predict(target_date)
        
        if result:
            total_data = result['total_data_points']
            today_data = result['today_data_points']
            predictions_count = result.get('predictions_count', 0)
            predictions_saved = result['predictions_saved']
            
            insert_log(
                f"LSTM-AE Prediction hoàn tất: {total_data} historical data, {today_data} today data, "
                f"{predictions_count} predictions generated, {predictions_saved} predictions saved",
                LogType.INFO
            )
            
            if predictions_saved > 0:
                insert_log(f"Đã lưu {predictions_saved} LSTM-AE predictions vào database", LogType.INFO)
            else:
                insert_log("Không có LSTM-AE predictions mới để lưu", LogType.WARNING)
                
            return True
        else:
            insert_log("LSTM-AE Prediction thất bại - không có kết quả trả về", LogType.ERROR)
            return False
            
    except Exception as e:
        insert_log(f"Lỗi khi chạy LSTM-AE prediction: {str(e)}", LogType.ERROR)
        return False

def run_lstm_prediction_after_crawl(target_date=None):
    try:
        from ..ml.lstm.predict import LSTM_Predictor
        from ..config import MLConfig
        
        predictor = LSTM_Predictor(
            historical_context=getattr(MLConfig, 'LSTM_WINDOW_CONTEXT', 4),
            model_path=getattr(MLConfig, 'LSTM_MODEL_PATH', None),
            scaler_path=getattr(MLConfig, 'SCALER_LSTM_MODEL_PATH', None),
            debug=False  # Tắt debug để tránh lỗi encoding
        )
        
        result = predictor.predict(target_date)
        
        if result:
            total_data = result['total_data_points']
            today_data = result['today_data_points']
            predictions_count = result.get('predictions_count', 0)
            predictions_saved = result['predictions_saved']
            
            insert_log(
                f"LSTM Prediction hoàn tất: {total_data} historical data, {today_data} today data, "
                f"{predictions_count} predictions generated, {predictions_saved} predictions saved",
                LogType.INFO
            )
            
            if predictions_saved > 0:
                insert_log(f"Đã lưu {predictions_saved} LSTM predictions vào database", LogType.INFO)
            else:
                insert_log("Không có LSTM predictions mới để lưu", LogType.WARNING)
                
            return True
        else:
            insert_log("LSTM Prediction thất bại - không có kết quả trả về", LogType.ERROR)
            return False
            
    except Exception as e:
        insert_log(f"Lỗi khi chạy LSTM prediction: {str(e)}", LogType.ERROR)
        return False

def run_prediction_after_crawl(target_date=None):
    """Chạy cả LSTM và LSTM AutoEncoder predictions sau khi crawl"""
    lstmae_success = run_lstmae_prediction_after_crawl(target_date)
    lstm_success = run_lstm_prediction_after_crawl(target_date)
    
    if lstmae_success and lstm_success:
        insert_log("Cả hai predictions (LSTM và LSTM-AE) đã hoàn thành thành công", LogType.INFO)
        return True
    elif lstmae_success or lstm_success:
        insert_log("Một trong hai predictions đã hoàn thành thành công", LogType.WARNING)
        return True
    else:
        insert_log("Cả hai predictions đều thất bại", LogType.ERROR)
        return False

def crawl_measurements_data(): 
    import time
    max_retries = 3
    retry_delays = [60, 120, 300]
    
    insert_log("Kiểm tra và refresh token trước khi crawl measurements data", LogType.INFO)
    if not api_client.ensure_token():
        insert_log("Không thể lấy token để crawl measurements data", LogType.ERROR)
        return None
    
    for attempt in range(max_retries):
        try: 
            insert_log(f"Thử crawl measurements data lần {attempt + 1}/{max_retries}", LogType.INFO)
            
            start_date = datetime.now().strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            time_range = "01:00-04:00"
            data = api_client.request(
                method="GET",
                endpoint="/api/scada/get_measurement_data_by_time",
                params={"start_date": start_date, "end_date": end_date, "time_range": time_range},
                timeout=90 
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
            error_msg = str(e)
            insert_log(f"Lần thử {attempt + 1} thất bại: {error_msg}", LogType.WARNING)
            
            if attempt < max_retries - 1:
                delay = retry_delays[attempt]
                insert_log(f"Đợi {delay}s trước khi thử lại measurements...", LogType.INFO)
                time.sleep(delay)
            else:
                insert_log(f"Đã thử {max_retries} lần crawl measurements và thất bại. Lỗi cuối: {error_msg}", LogType.ERROR)
                if "400" in error_msg and "Bad Request" in error_msg:
                    try:
                        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                        insert_log(f"Thử test crawl measurements với ngày hôm qua: {yesterday} (không lưu DB)", LogType.INFO)
                        
                        test_data = api_client.request(
                            method="GET",
                            endpoint="/api/scada/get_measurement_data_by_time",
                            params={"start_date": yesterday, "time_range": time_range},
                            timeout=90
                        )
                        
                        if test_data:
                            insert_log(f"Test crawl measurements với ngày hôm qua thành công: {len(test_data)} bản ghi (không lưu DB)", LogType.INFO)
                        else:
                            insert_log("Test crawl measurements với ngày hôm qua không có dữ liệu", LogType.WARNING)
                            
                    except Exception as e2:
                        insert_log(f"Test crawl measurements với ngày hôm qua thất bại: {str(e2)}", LogType.WARNING)
                
                return None
    
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