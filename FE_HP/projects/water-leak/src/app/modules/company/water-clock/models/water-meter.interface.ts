export interface WaterMeter {
  id: string;
  name: string;
  branchName: string | number;
  status: 'Normal' | 'On fixing' | 'Anomaly detected';
  installationDate?: string | Date;
  selected?: boolean;
  expanded?: boolean;
  anomalyDetected?: number;
}

export interface WaterMeterFilter {
  searchTerm: string;
  statusFilter: string;
}
