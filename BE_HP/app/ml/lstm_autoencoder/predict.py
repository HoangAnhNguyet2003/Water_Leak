import torch
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime, timedelta, timezone
import os
import joblib

from ...extensions import get_db
from ...utils import to_object_id
from ...config import MLConfig
try:
    from .lstm_autoencoder import LSTMAE
except ImportError as e:
    print(f"Warning: Could not import LSTMAE model: {e}")
    LSTMAE = None


class LSTMAEPredictor:
    def __init__(self, model_path=None, config=None, debug=False):
        default_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pretrained_weights', 'lstm_ae.pth'))
        self.model_path = model_path or default_path
        self.config = config or {
            'input_size': 1,
            'hidden_size': 32,
            'num_layers': 1,
            'dropout_ratio': 0.1,
            'seq_len': 168,
            'use_act': True
        }
        self.debug = debug
        self.model = None
        self.scaler = MinMaxScaler()
        scaler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pretrained_weights', 'scaler.pkl'))
        if os.path.exists(scaler_path):
            with open(scaler_path, 'rb') as f:
                self.scaler = joblib.load(f)
            if self.debug:
                print('Loaded pretrained scaler from', scaler_path)
        else: 
            if self.debug:
                print('No pretrained scaler found at', scaler_path, '; using default MinMaxScaler')
        self.threshold = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def load_model(self):
        if LSTMAE is None:
            print("Không tìm thấy lớp LSTM-AutoEncoder!")
            return

        self.model = LSTMAE(**self.config)
        if os.path.exists(self.model_path):
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            print(f"Đã tải mô hình từ {self.model_path}")
        else:
            print(f"Không tìm thấy tệp mô hình tại {self.model_path}, sử dụng mô hình chưa được huấn luyện")
        self.model.to(self.device)
        self.model.eval()

    def prepare_data(self, data):
        arr = np.array(data).reshape(-1, 1)
        data_scaled = self.scaler.transform(arr)
        return data_scaled.flatten()

    def calculate_threshold(self, meter_id: str, days_back=7, percentile=90):
        try:
            if self.model is None:
                self.load_model()

            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back)

            db = get_db()

            historical_data = list(db.meter_measurements.find({
                "meter_id": to_object_id(meter_id),
                "measurement_time": {"$gte": start_date, "$lte": end_date}
            }).sort("measurement_time", 1))
            if len(historical_data) < self.config['seq_len'] * 2:
                historical_data = list(db.meter_measurements.find({
                    "meter_id": to_object_id(meter_id)
                }).sort("measurement_time", 1))


            flow_rates = [float(row.get('instant_flow', 0.0)) for row in historical_data]
            flow_data_scaled = self.prepare_data(flow_rates)

            seq_len = self.config['seq_len']
            if len(flow_data_scaled) < seq_len:
                pad_len = seq_len - len(flow_data_scaled)
                flow_data_scaled = np.concatenate((np.zeros(pad_len, dtype=flow_data_scaled.dtype), flow_data_scaled))

            sequences = []
            for i in range(len(flow_data_scaled) - seq_len + 1):
                seq = flow_data_scaled[i:i + seq_len]
                sequences.append(seq)

            sequences = np.array(sequences)[:, :, np.newaxis]

            reconstruction_errors = []
            self.model.eval()
            with torch.no_grad():
                for seq in sequences:
                    seq_tensor = torch.FloatTensor(seq).unsqueeze(0).to(self.device)
                    reconstructed = self.model(seq_tensor)
                    point_errors = torch.mean((seq_tensor - reconstructed) ** 2, dim=2)
                    last_error = point_errors[0, -1].item()
                    reconstruction_errors.append(last_error)

            self.threshold = float(np.percentile(reconstruction_errors, percentile))

            return self.threshold

        except Exception as e:
            print(f"Lỗi khi tính ngưỡng: {e}")
            import traceback
            traceback.print_exc()
            return 0.015

    def predict_one(self, meter_id: str, current_flow_rate):
        try:
            if self.model is None:
                self.load_model()

            db = get_db()

            recent_limit = self.config['seq_len'] - 1
            recent_data = list(db.meter_measurements.find({
                "meter_id": to_object_id(meter_id)
            }).sort("measurement_time", -1).limit(recent_limit))

            if len(recent_data) < recent_limit:
                final_threshold = self.calculate_threshold(meter_id)

            flow_rates = [float(row.get('instant_flow', 0.0)) for row in reversed(recent_data)] + [float(current_flow_rate)]
            flow_data_scaled = self.prepare_data(flow_rates)

            seq_len = self.config['seq_len']
            if len(flow_data_scaled) < seq_len:
                pad_len = seq_len - len(flow_data_scaled)
                flow_data_scaled = np.concatenate((np.zeros(pad_len, dtype=flow_data_scaled.dtype), flow_data_scaled))
            current_seq = flow_data_scaled.reshape(1, seq_len, 1)
            current_seq_tensor = torch.FloatTensor(current_seq).to(self.device)

            self.model.eval()
            with torch.no_grad():
                reconstructed = self.model(current_seq_tensor)
                point_errors = torch.mean((current_seq_tensor - reconstructed) ** 2, dim=2)
                reconstruction_error = float(point_errors[0, -1].item())
                

                reconstructed_inverse = self.scaler.inverse_transform(reconstructed.cpu().numpy().reshape(-1, 1)).reshape(1, seq_len, 1)
                if self.debug:
                    print(f"Reconstructed (unscaled): {reconstructed_inverse.flatten()[144:]}")
                    print(f"Current sequence (unscaled): {flow_rates[144:]}")

                original_last_point = float(current_seq_tensor[0, -1, 0].item())
                reconstructed_last_point = float(reconstructed[0, -1, 0].item())

                if not hasattr(self.scaler, 'scale_'):
                    self.scaler.fit(np.array(flow_rates).reshape(-1, 1))
                
                original_unscaled = float(self.scaler.inverse_transform([[original_last_point]])[0][0])
                reconstructed_unscaled = float(self.scaler.inverse_transform([[reconstructed_last_point]])[0][0])
                if self.debug:
                    print(f"Last point (scaled): Original={original_last_point}, Reconstructed={reconstructed_last_point}, Error={reconstruction_error}")
                    print(f"Original: {original_unscaled}, Reconstructed: {reconstructed_unscaled}, Error: {reconstruction_error}")

            final_threshold = self.threshold if self.threshold is not None else self.calculate_threshold(meter_id)

            is_anomaly = reconstruction_error > final_threshold
            if reconstructed_unscaled > original_unscaled:
                is_anomaly = False

            flow_diff_ratio = abs(reconstructed_unscaled - original_unscaled) / max(abs(original_unscaled), 1e-3)
            error_factor = min(reconstruction_error / max(final_threshold, 1e-8), 3.0)

            if is_anomaly:
                combined_factor = 0.7 * error_factor + 0.3 * flow_diff_ratio
                confidence = min(0.95, 0.60 + 0.35 * min(combined_factor, 1.0))
            else:
                normal_factor = 1.0 - min(error_factor / 2.0, 1.0)
                confidence = max(0.75, 0.75 + 0.20 * normal_factor)


            return is_anomaly, confidence, reconstruction_error, final_threshold, reconstructed_unscaled

        except Exception as e:
            print(f"Lỗi trong prediction: {e}")
            import traceback
            traceback.print_exc()
            fallback_threshold = 0.015
            return False, 0.95, 0.0, fallback_threshold


predictor = LSTMAEPredictor(config=MLConfig.LSTM_AE_CONFIG, model_path=MLConfig.LSTM_AE_MODEL_PATH, debug=False)