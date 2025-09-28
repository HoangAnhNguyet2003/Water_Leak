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
}
