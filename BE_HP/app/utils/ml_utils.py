import torch
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler

device = 'cuda' if torch.cuda.is_available() else 'cpu'

def preprocess_data_with_dates_json(data, scaler: MinMaxScaler = None, seq_len=6, fit_scaler=True):
    cleaned = [] 
    
    if scaler is None:
        scaler = MinMaxScaler()
        
    for item in data:
        try:
            if isinstance(item['measurement_time'], str):
                t = datetime.strptime(item['measurement_time'], '%Y-%m-%dT%H:%M:%S')
            else:
                t = item['measurement_time'] 

            flow = float(item['instant_flow'])
            cleaned.append({'Ngày tháng': t, 'instant_flow': flow})
        except (KeyError, ValueError, TypeError):
            continue

    cleaned.sort(key=lambda x: x['Ngày tháng'])
    flows = np.array([d['instant_flow'] for d in cleaned]).reshape(-1, 1)

    if fit_scaler:
        flows_norm = scaler.fit_transform(flows)
    else:
        flows_norm = scaler.transform(flows)

    for i, val in enumerate(flows_norm):
        cleaned[i]['lưu_lượng_norm'] = val[0]

    sequences = []
    seq_start_dates = []
    n = len(cleaned)

    for i in range(n - seq_len + 1):
        start_time = cleaned[i]['Ngày tháng']

        if start_time.minute == 0:
            end_time = cleaned[i + seq_len - 1]['Ngày tháng']

            if start_time.date() == end_time.date():
                seq_vals = [cleaned[j]['lưu_lượng_norm'] for j in range(i, i + seq_len)]
                sequences.append(seq_vals)
                seq_start_dates.append(start_time)
    if sequences:
        sequences = np.array(sequences)[:, :, np.newaxis]  # (N, seq_len, 1)
        seq_start_dates = np.array(seq_start_dates)
    else:
        sequences = np.empty((0, seq_len, 1))
        seq_start_dates = np.array([])
           
    return sequences, seq_start_dates, scaler

def calculate_mnf(
    df: pd.DataFrame,
    timestamp_col: str = 'measurement_time',
    flow_col: str = 'instant_flow',
    date: str = None,
    start_hour: int = 1,
    end_hour: int = 4,
    min_data_ratio: float = 0.5
) -> dict:
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col])

    if date is not None:
        df = df[df[timestamp_col].dt.strftime('%Y-%m-%d') == date]

    df['hour'] = df[timestamp_col].dt.hour

    night_mask = (df['hour'] >= start_hour) & (df['hour'] < end_hour)
    night_df = df[night_mask].copy()

    if night_df.empty:
        return {}

    freq_minutes = 10
    expected_points = int((end_hour - start_hour) * 60 / freq_minutes)
    min_points = max(1, int(expected_points * min_data_ratio))

    mnf_results = {}

    flow_vals = df[flow_col].dropna().values

    if len(flow_vals) < min_points:
        mnf = np.nan
    else:
        mnf = np.median(flow_vals)
    return mnf

def fit_global_scaler_with_data(all_meter_data):
    if not all_meter_data:
        return None
        
    df = pd.DataFrame(all_meter_data)
    flow_data = df['instant_flow'].values.reshape(-1, 1)
    
    scaler = MinMaxScaler()
    scaler.fit(flow_data)
    
    return scaler

def get_mae_threshold(model, scaler, sequences):
    model.eval()

    mae_seq = []
    with torch.inference_mode():

        for seq in sequences:
            torch_seq = torch.from_numpy(seq).unsqueeze(0).to(device).float()
            torch_seq = torch_seq.to(device)
            output = model(torch_seq)

            output_np = output.squeeze(0).cpu().numpy()
            _reconstructed = scaler.inverse_transform(output_np)
            _original = scaler.inverse_transform(seq)

            mae = np.max(np.abs(_original - _reconstructed))
            mae_seq.append(mae)

    return {
        'mae_low_threshold': np.percentile(mae_seq, 20),
        'mae_high_threshold': np.percentile(mae_seq, 80)
    }

def predict_lstmae(model, smp, mnf, mnf_threshold, scaler, mae_low_threshold=0.02, mae_high_threshold=0.1):
    model.eval()
    smp_tensor = torch.from_numpy(smp).unsqueeze(0).to(device).float()
    with torch.no_grad():
        output = model(smp_tensor)

    output_np = output.squeeze(0).cpu().numpy()
    _reconstructed = scaler.inverse_transform(output_np)
    _original = scaler.inverse_transform(smp)

    max_mae = np.max(np.abs(_original - _reconstructed))

    mnf_excess_pct = ((mnf - mnf_threshold) / mnf_threshold * 100) if mnf > mnf_threshold else 0.0
    mae_excess_pct = ((max_mae - mae_high_threshold) / mae_high_threshold * 100) if max_mae > mae_high_threshold else 0.0

    status = "normal"
    confidence = None

    if np.isnan(mnf) or np.isnan(max_mae):
        return {
            'original': _original,
            'max_mae': max_mae,
            'status': "invalid_data",
            'confidence': "none",
            'avg_instant_flow': np.mean(_original),
            'pred_flow': np.mean(_reconstructed),
        }

    if max_mae > mae_high_threshold:
        status = "leak"
        if mae_excess_pct >= 50:
            confidence = "NNcao"
        elif mae_excess_pct >= 20:
            confidence = "NNTB"
        else:
            confidence = "NNthap"
    elif mnf > mnf_threshold and max_mae < mae_low_threshold:
        status = "leak"
        if mnf_excess_pct >= 50:
            confidence = "NNcao"
        elif mnf_excess_pct >= 20:
            confidence = "NNTB"
        else:
            confidence = "NNthap"
    else:
        status = "normal"

    return {
        'original': _original,
        'max_mae': max_mae,
        'status': status,
        'confidence': confidence,
        'avg_instant_flow': np.mean(_original),
        'pred_flow': np.mean(_reconstructed),
    }
