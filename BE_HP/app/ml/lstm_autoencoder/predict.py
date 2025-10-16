import torch
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime, timedelta, timezone
import os
import joblib

from ...extensions import get_db
from ...utils import to_object_id, get_vietnam_now, VIETNAM_TZ
from ...utils.ml_utils import preprocess_data_with_dates_json, calculate_mnf, get_mae_threshold, fit_global_scaler_with_data, predict_lstmae
from ...config import MLConfig
try:
    from .lstm_autoencoder import LSTMAE
except ImportError as e:
    print(f"Warning: Could not import LSTMAE model: {e}")
    LSTMAE = None

ok_meters = [
    'DU LỄ 1',
    'DU LỄ 2',
    'DU LỄ 3',
    'DU LỄ 4',
    'TÂN VIÊN 1',
    'TÂN VIÊN 2',
    'TÂN VIÊN 3',
  ]

class LSTMAEPredictor:
    def __init__(self, historical_context=None, model_path=None, config=None, debug=False):
        default_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pretrained_weights', 'lstm_ae.pth'))
        self.historical_context = historical_context or 14
        self.model_path = model_path or default_path
        self.config = config or {
            'input_size': 1,
            'hidden_size': 64,
            'num_layers': 2,
            'dropout_ratio': 0.1,
            'seq_len': 6,
            'use_act': True
        }
        self.debug = debug
        self.model = None
        self.scaler = MinMaxScaler()
        self.threshold = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def load_model(self):
        if LSTMAE is None:
            print("Không tìm thấy lớp LSTM-AutoEncoder!")
            return False

        self.model = LSTMAE(**self.config)
        if os.path.exists(self.model_path):
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            if self.debug:
                print(f"Đã tải mô hình từ {self.model_path}")
        else:
            print(f"Model file not found: {self.model_path}")
            return False
            
        self.model.to(self.device)
        self.model.eval()
        return True

    def prepare_data(self, data, seq_len=6, fit_scaler=False):
        sequences, seq_start_dates, scaler = preprocess_data_with_dates_json(
            data, 
            scaler=self.scaler, 
            seq_len=seq_len, 
            fit_scaler=fit_scaler
        )
        
        if fit_scaler:
            self.scaler = scaler
            
        return sequences, seq_start_dates
    
    def calculate_threshold(self, meter_data_or_all_data, single_meter=True):
        if single_meter:
            df = pd.DataFrame(meter_data_or_all_data)
            mnf = calculate_mnf(df, timestamp_col='measurement_time')
            seqs, _ = self.prepare_data(meter_data_or_all_data, seq_len=self.config['seq_len'])
            mae_thresholds = get_mae_threshold(self.model, self.scaler, seqs)
            return mnf, mae_thresholds
        else:
            if not meter_data_or_all_data:
                return {}
                
            df = pd.DataFrame(meter_data_or_all_data)
            thresholds = {}
            
            for meter_name in ok_meters:
                meter_data = df[df['meter_name'] == meter_name].to_dict('records')
                
                if len(meter_data) > 0:
                    try:
                        mnf, mae_thresholds = self.calculate_threshold(meter_data, single_meter=True)
                        thresholds[meter_name] = {
                            'mnf': mnf,
                            'mae_thresholds': mae_thresholds
                        }
                        
                        if self.debug:
                            print(f"Meter {meter_name} - MNF: {mnf}, MAE thresholds: {mae_thresholds}")
                            
                    except Exception as e:
                        if self.debug:
                            print(f"Lỗi tính threshold cho meter {meter_name}: {e}")
                        continue
            
            return thresholds

    def get_time_range(self):
        now = get_vietnam_now()
        yesterday = now.date() - timedelta(days=1)
        end_time = datetime.combine(yesterday, datetime.max.time()).replace(tzinfo=VIETNAM_TZ)
        start_time = end_time - timedelta(days=self.historical_context)
        return start_time, end_time
    
    def get_today_time_range(self, target_date=None):
        if target_date is None:
            now = get_vietnam_now()
            target_date = now.date()
        elif isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        start_time = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=VIETNAM_TZ)
        end_time = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=VIETNAM_TZ)
        return start_time, end_time

    def fetch_meter_data(self, start_time, end_time):
        db = get_db()
        all_meter_data = []
        
        for meter_name in ok_meters:
            meter = db.meters.find_one({"meter_name": meter_name})
            if not meter:
                if self.debug:
                    print(f"Không tìm thấy meter: {meter_name}")
                continue
                
            meter_id = meter["_id"]
            
            measurements = list(db.meter_measurements.find({
                "meter_id": meter_id,
                "measurement_time": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("measurement_time", 1))
            
            if self.debug:
                print(f"Meter {meter_name}: {len(measurements)} measurements")
            
            for measurement in measurements:
                measurement['meter_name'] = meter_name
                measurement['meter_id'] = str(meter_id)
                all_meter_data.append(measurement)
        
        return all_meter_data

    def fit_global_scaler(self, all_meter_data):
        if not all_meter_data:
            return False
            
        scaler = fit_global_scaler_with_data(all_meter_data)
        if scaler is None:
            return False
            
        self.scaler = scaler
        
        if self.debug:
            df = pd.DataFrame(all_meter_data)
            flow_data = df['instant_flow'].values
            print(f"Đã fit scaler với {len(flow_data)} điểm dữ liệu")
            print(f"Scaler min: {self.scaler.data_min_[0]:.4f}, max: {self.scaler.data_max_[0]:.4f}")
        
        return True

    def predict_today_data(self, all_meter_data, thresholds):
        if not all_meter_data or not thresholds:
            return []
            
        predictions = []
        df = pd.DataFrame(all_meter_data)
        
        for meter_name in ok_meters:
            if meter_name not in thresholds:
                continue
                
            meter_data = df[df['meter_name'] == meter_name].to_dict('records')
            if len(meter_data) == 0:
                continue
                
            try:
                meter_thresholds = thresholds[meter_name]
                mnf = meter_thresholds['mnf']
                mae_thresholds = meter_thresholds['mae_thresholds']
                
                seqs, seq_dates = self.prepare_data(meter_data, seq_len=self.config['seq_len'])
                
                for i, (seq, seq_date) in enumerate(zip(seqs, seq_dates)):
                    pred_result = predict_lstmae(
                        model=self.model,
                        smp=seq,
                        mnf=mnf,
                        mnf_threshold=mae_thresholds.get('mnf_threshold', mnf * 1.2), 
                        scaler=self.scaler,
                        mae_low_threshold=mae_thresholds.get('low', 0.02),
                        mae_high_threshold=mae_thresholds.get('high', 0.1)
                    )
                    
                    predictions.append({
                        'meter_name': meter_name,
                        'prediction_time': seq_date,
                        'status': pred_result['status'],
                        'confidence': pred_result.get('confidence', 'Unknown'),
                        'avg_instant_flow': pred_result['avg_instant_flow'],
                        'pred_flow': pred_result['pred_flow'],
                        'max_mae': pred_result['max_mae']
                    })
                    
            except Exception as e:
                if self.debug:
                    print(f"Lỗi predict cho meter {meter_name}: {e}")
                continue
                
        return predictions
    
    def save_predictions_to_db(self, predictions):
        if not predictions:
            return 0
            
        db = get_db()
        lstm_ae_model = db.ai_models.find_one({"name": "lstm_autoencoder"})
        if not lstm_ae_model:
            lstm_ae_model = {
                "name": "lstm_autoencoder",
                "_id": to_object_id()
            }
            db.ai_models.insert_one(lstm_ae_model)
        
        model_id = lstm_ae_model["_id"]
        
        prediction_docs = []
        for pred in predictions:
            meter = db.meters.find_one({"meter_name": pred['meter_name']})
            if not meter:
                continue
                
            prediction_docs.append({
                "meter_id": meter["_id"],
                "model_id": model_id,
                "prediction_time": pred['prediction_time'],
                "predicted_label": pred['status'],
                "confidence": pred['confidence'],
                "recorded_instant_flow": float(pred['avg_instant_flow'])
            })
        
        if prediction_docs:
            result = db.predictions.insert_many(prediction_docs)
            return len(result.inserted_ids)
        
        return 0

    def predict(self, target_date=None):
        try:
            if self.model is None:
                if not self.load_model():
                    print("Không thể load model")
                    return None
            
            start_time, end_time = self.get_time_range()
            all_meter_data = self.fetch_meter_data(start_time, end_time)
            
            if not self.fit_global_scaler(all_meter_data):
                print("Không thể fit scaler")
                return None
            
            thresholds = self.calculate_threshold(all_meter_data, single_meter=False)
            
            today_start, today_end = self.get_today_time_range(target_date)
            today_meter_data = self.fetch_meter_data(today_start, today_end)
            
            if not today_meter_data:
                print("Không có dữ liệu ngày hôm nay để predict")
                return {
                    'total_data_points': len(all_meter_data),
                    'today_data_points': 0,
                    'scaler_fitted': True,
                    'thresholds': thresholds,
                    'predictions_saved': 0,
                    'time_range': {
                        'historical_start': start_time.isoformat(),
                        'historical_end': end_time.isoformat(),
                        'today_start': today_start.isoformat(),
                        'today_end': today_end.isoformat()
                    }
                }
            
            predictions = self.predict_today_data(today_meter_data, thresholds)
            
            saved_count = self.save_predictions_to_db(predictions)
            
            return {
                'total_data_points': len(all_meter_data),
                'today_data_points': len(today_meter_data),
                'predictions_count': len(predictions),
                'predictions_saved': saved_count,
                'scaler_fitted': True,
                'thresholds': thresholds,
                'time_range': {
                    'historical_start': start_time.isoformat(),
                    'historical_end': end_time.isoformat(),
                    'today_start': today_start.isoformat(),
                    'today_end': today_end.isoformat()
                }
            }
            
        except Exception as e:
            print(f"Lỗi trong hàm predict: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None


def get_predictor():
    from ...config import MLConfig
    return LSTMAEPredictor(
        historical_context=MLConfig.HISTORICAL_DATA_DAYS, 
        config=MLConfig.LSTM_AE_CONFIG, 
        model_path=MLConfig.LSTM_AE_MODEL_PATH, 
        debug=False
    )

predictor = None

def init_predictor():
    global predictor
    if predictor is None:
        predictor = get_predictor()
    return predictor