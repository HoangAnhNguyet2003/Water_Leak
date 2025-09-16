export interface DashboardReceivedData {
  userCount: number;
  activeMeterCount: number;
  recentLogsCount: number;
}
export interface StatCard {
  id: string;
  title: string;
  value: number;
  description: string;
  type: string;
}
export type DashBoardData = {
  userCount: number;
  activeMeterCount: number;
  recentLogsCount: number;
}

