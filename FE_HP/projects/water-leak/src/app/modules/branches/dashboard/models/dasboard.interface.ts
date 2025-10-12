export interface Dashboard {
  _id: string;
  branch_id: string;
  meter_name: string;
  location?: string; 
  leakDays?: number; 
  selected?: boolean;
  expanded?: boolean;
  anomalyDetected?: number;
  prediction?: {
    meter_name: string;
    prediction_time: string | Date;
    model_name: string;
    predicted_label: string;
  } | null;
}