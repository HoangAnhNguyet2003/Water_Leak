export interface RawMeterData {
  _id: string;
  branch_id: string;
  meter_name: string;
  installation_time?: any;
  branchName?: string;
  threshold?: any;
  measurement?: any;
  repair?: any;
  selected?: boolean;
  expanded?: boolean;
  anomalyDetected?: boolean;
  prediction?: any;
  predictions?: any[];
  latitude?: number;
  longitude?: number;
  lat?: number;
  lng?: number;
}
