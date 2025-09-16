export interface WaterMeter {
  id: string | number;
  name: string;
  branchName: string | number;
  installationDate?: string | Date;
  status: WaterMeterStatus;
}

export enum WaterMeterStatus {
  NORMAL = 'normal',
  ANOMALY = 'anomaly',
  LOST_CONNECTION = 'lost_connection'
}
