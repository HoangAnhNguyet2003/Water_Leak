export interface ManualModel {
  _id: string;
  branch_id: string;
  meter_name: string;
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
  } | null;
  selected?: boolean;
  expanded?: boolean;
  anomalyDetected?: number;
}
