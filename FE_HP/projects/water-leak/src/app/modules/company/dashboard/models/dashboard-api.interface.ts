export interface DashBoardData {
  id: string | number;
  name: string;
  branchName: string | number;
  installationDate?: string | Date;
  status: DashBoardDataStatus;
  meter_data: {
    id: string | number;
    name: string;
    status: DashBoardDataStatus;
  }
}

export enum DashBoardDataStatus {
  NORMAL = 'normal',
  ANOMALY = 'anomaly',
  LOST_CONNECTION = 'lost_connection'
}