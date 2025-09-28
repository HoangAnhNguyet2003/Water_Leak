export interface WaterMeter {
  _id: string;
  branch_id: string;
  meter_name: string;
  installation_time: string | Date | null;
  branchName?: string;
  threshold?: {
    id: string;
    meter_id: string;
    set_time: string | Date;
    threshold_value: number;
  } | null;
  measurement?: {
    id: string;
    meter_id: string;
    measurement_time: string | Date;
    instant_flow: number;
    instant_pressure: number;
  } | null;
  repair?: {
    _id: string;
    meter_id: string;
    recorded_time: string;
    repair_time: string;
    leak_reason?: string;
  } | null;
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

export interface WaterMeterFilter {
  searchTerm: string;
  statusFilter: string;
  thresholdOperator?: '>' | '<' | '=';
  thresholdValue?: number;
}
