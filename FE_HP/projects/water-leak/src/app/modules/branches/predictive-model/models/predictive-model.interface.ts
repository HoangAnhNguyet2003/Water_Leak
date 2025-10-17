export interface PredictiveModel {
  _id: string;
  branch_id: string;
  meter_name: string;
  prediction?: {
    meter_name: string;
    prediction_time: string | Date;
    model_name: string;
    predicted_label: string;
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
