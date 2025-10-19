export interface Dashboard {
  _id: string;
  branch_id: string;
  meter_name: string;

  longitude?: number;
  latitude?: number;

  leakDays?: number;
  selected?: boolean;
  expanded?: boolean;
  anomalyDetected?: number;

  prediction?: {
    meter_name: string;
    prediction_time: string | Date;
    model_name: string;
    predicted_label: string;
    confidence: string | number;
  } | null;

  predictions?: PredictionDetail[];
}

export interface PredictionDetail {
  _id: string;
  meter_id: string;
  model: {
    _id: string;
    name: string;
  } | null;
  model_name: string | null;
  prediction_time: string | Date;
  predicted_threshold?: number;
  predicted_label: string;
  confidence: string | number;
  recorded_instant_flow?: number;
}
