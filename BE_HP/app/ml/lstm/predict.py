import os
import pandas as pd
import numpy as np
from keras.models import load_model, clone_model
from keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime, timedelta, timezone, date
import pickle

from ...extensions import get_db
from ...utils import to_object_id
from ...utils.ml_utils import preprocess_data_lstm
from ...config import MLConfig

ok_meters = [
    'DU LỄ 1',
    'DU LỄ 2',
    'DU LỄ 3',
    'DU LỄ 4',
    'TÂN VIÊN 1',
    'TÂN VIÊN 2',
    'TÂN VIÊN 3',
]

class LSTM_Predictor:
    def __init__(self, historical_context=None, model_path=None, scaler_path=None, debug=True):
        default_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pretrained_weights', 'base_lstm_model.h5'))

        self.historical_context = historical_context or 4
        self.model_path = model_path or default_path
        self.debug = debug
        self.base_model = None
        self.scaler = MinMaxScaler()
        
        self._load_base_model()

    def _load_base_model(self):
        try:
            if os.path.exists(self.model_path):
                self.base_model = load_model(self.model_path)
                if self.debug:
                    print(f"Model loaded from {self.model_path}")
            else:
                if self.debug:
                    print(f"Model not found at {self.model_path}")
                return False
        except Exception as e:
            if self.debug:
                print(f"Error loading model: {e}")
            return False
        return True
    
    def prepare_data(self, values, look_back):
        X = []
        for i in range(len(values) - look_back + 1):
            X.append(values[i:i + look_back])
        return np.array(X).reshape(-1, look_back, 1)

    def classify_difference(self, true_vals, pred_vals):
        levels = []
        for true, pred in zip(true_vals, pred_vals):
            if pred == 0 or np.isnan(pred) or np.isnan(true):
                levels.append("normal")
                continue
            diff_percent = abs(true - pred) / max(abs(pred), 1e-6) * 100
            if diff_percent < 10:
                levels.append("NNthap")
            elif diff_percent <= 25:
                levels.append("NNTB")
            else:
                levels.append("NNcao")
        return levels

    def adjust_levels_3days(self, true_vals, levels):
        n = len(levels)
        adjusted_levels = levels.copy()
        
        for i in range(n - 2):  
            window_levels = levels[i:i+3]
            window_true = true_vals[i:i+3]

            cao_indices = [j for j, l in enumerate(window_levels) if l == "NNcao"]
            thap_indices = [j for j, l in enumerate(window_levels) if l == "NNthap"]

            if cao_indices and thap_indices:
                first_cao_idx = cao_indices[0]

                if first_cao_idx == 0 or first_cao_idx == 2:
                    continue
                first_cao_val = window_true[first_cao_idx]

                for thap_idx in thap_indices:
                    thap_val = window_true[thap_idx]
                    if thap_idx < first_cao_idx and thap_val <= first_cao_val * 0.7:
                        adjusted_levels[i + thap_idx] = "NNTB"
        
        return adjusted_levels
    
    def get_time_range(self):
        now = datetime.now(timezone.utc)
        yesterday = now.date() - timedelta(days=1)
        end_time = datetime.combine(yesterday, datetime.max.time()).replace(tzinfo=timezone.utc)
        start_time = end_time - timedelta(days=self.historical_context)
        return start_time, end_time
    
    def get_today_time_range(self, target_date=None):
        if target_date is None:
            now = datetime.now(timezone.utc)
            target_date = now.date()
        elif isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        start_time = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_time = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        return start_time, end_time
    
    def fetch_meter_data(self, start_time, end_time):
        db = get_db()
        all_meter_data = []
        
        for meter_name in ok_meters:
            meter = db.meters.find_one({"meter_name": meter_name})
            if not meter:
                continue
                
            meter_id = meter["_id"]
            
            measurements = list(db.meter_measurements.find({
                "meter_id": meter_id,
                "measurement_time": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("measurement_time", 1))
            
            for measurement in measurements:
                measurement['meter_name'] = meter_name
                measurement['meter_id'] = str(meter_id)
                all_meter_data.append(measurement)
        
        return all_meter_data

    def fine_tune_model(self, meter_data, scaler):
        daily_averages, dates, _ = preprocess_data_lstm(
            meter_data, 
            scaler,
            fit_scaler=True
        )
        
        X_ft = self.prepare_data(daily_averages, self.historical_context)
        y_ft = daily_averages[self.historical_context - 1:]
        
        model = clone_model(self.base_model)
        model.set_weights(self.base_model.get_weights())
        model.compile(
            optimizer=Adam(learning_rate=1e-4), 
            loss='mse'
        )
        
        model.fit(
            X_ft, y_ft, 
            epochs=10, 
            batch_size=32, 
            verbose=0
        )
        
        return model, daily_averages, dates

    def predict_meter(self, meter_name, model, scaler, daily_averages, dates, today_data=None, target_date=None):
        try:
            if len(daily_averages) >= self.historical_context:
                last_sequence = daily_averages[-self.historical_context:]
                X_pred = last_sequence.reshape(1, self.historical_context, 1)
                pred_scaled = model.predict(X_pred, verbose=0).flatten()
                pred_real = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
                
                today_actual_flow = 0.0
                if today_data:
                    meter_today_data = [d for d in today_data if d.get('meter_name') == meter_name]
                    if meter_today_data:
                        flows = [d.get('instant_flow', 0) for d in meter_today_data if d.get('instant_flow') is not None]
                        today_actual_flow = sum(flows) / len(flows) if flows else 0.0
                
                if today_actual_flow > 0:
                    levels = self.classify_difference([today_actual_flow], pred_real)
                else:
                    pred_val = pred_real[0]
                    if pred_val < 1.0:
                        level = "NNthap"
                    elif pred_val <= 3.0:
                        level = "NNTB"  
                    else:
                        level = "NNcao"
                    levels = [level]
                
                if target_date is None:
                    target_date = datetime.now(timezone.utc).date()
                elif isinstance(target_date, str):
                    target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
                
                results = [{
                    'meter_name': meter_name,
                    'date': target_date,
                    'avg_instant_flow': float(today_actual_flow),
                    'pred_flow': float(pred_real[0]),
                    'NN_level': levels[0]
                }]
                
                return results
            
            return []
            
        except Exception as e:
            if self.debug:
                print(f"Lỗi predict meter {meter_name}: {e}")
            return []

    def save_predictions_to_db(self, predictions):
        if not predictions:
            return 0
            
        db = get_db()
        
        lstm_model = db.ai_models.find_one({"name": "lstm"})
        if not lstm_model:
            lstm_model = {
                "name": "lstm",
                "_id": to_object_id()
            }
            db.ai_models.insert_one(lstm_model)
        
        model_id = lstm_model["_id"]
        
        prediction_docs = []
        for pred in predictions:
            meter = db.meters.find_one({"meter_name": pred['meter_name']})
            if not meter:
                continue
            
            if pred['NN_level'] in ['NNcao', 'NNTB']:
                label = 'leak'
            else:
                label = 'normal'
            
            if isinstance(pred['date'], str):
                prediction_time = datetime.strptime(pred['date'], '%Y-%m-%d')
            elif hasattr(pred['date'], 'date'):
                prediction_time = pred['date']
            else:
                prediction_time = datetime.combine(pred['date'], datetime.min.time())
            
            prediction_docs.append({
                "meter_id": meter["_id"],
                "model_id": model_id,
                "prediction_time": prediction_time,
                "predicted_label": label,
                "confidence": pred['NN_level'],
                "recorded_instant_flow": pred['avg_instant_flow'],
            })
        
        if prediction_docs:
            result = db.predictions.insert_many(prediction_docs)
            return len(result.inserted_ids)
            
        return 0

    def predict(self, target_date=None):
        start_time, end_time = self.get_time_range()
        all_meter_data = self.fetch_meter_data(start_time, end_time)
        
        today_start, today_end = self.get_today_time_range(target_date)
        today_meter_data = self.fetch_meter_data(today_start, today_end)
        
        all_predictions = []
        df_historical = pd.DataFrame(all_meter_data)
        for meter_name in ok_meters:
            meter_historical = df_historical[df_historical['meter_name'] == meter_name].to_dict('records')
            
            if not meter_historical:
                continue

            _scaler = MinMaxScaler()
            model, daily_averages, dates = self.fine_tune_model(meter_historical, _scaler)
            
            predictions = self.predict_meter(meter_name, model, _scaler, daily_averages, dates, today_meter_data, target_date)
            all_predictions.extend(predictions)
        
        saved_count = self.save_predictions_to_db(all_predictions)
        
        return {
            'total_data_points': len(all_meter_data),
            'today_data_points': len(today_meter_data),
            'predictions_count': len(all_predictions),
            'predictions_saved': saved_count,
            'time_range': {
                'historical_start': start_time.isoformat(),
                'historical_end': end_time.isoformat(),
                'today_start': today_start.isoformat(),
                'today_end': today_end.isoformat()
            }
        }


def get_predictor():
    from ...config import MLConfig
    return LSTM_Predictor(
        historical_context=getattr(MLConfig, 'LSTM_WINDOW_CONTEXT', 4), 
        model_path=getattr(MLConfig, 'LSTM_MODEL_PATH', None), 
        scaler_path=getattr(MLConfig, 'SCALER_LSTM_MODEL_PATH', None),
        debug=False
    )

predictor = None

def init_predictor():
    global predictor
    if predictor is None:
        predictor = get_predictor()
    return predictor

