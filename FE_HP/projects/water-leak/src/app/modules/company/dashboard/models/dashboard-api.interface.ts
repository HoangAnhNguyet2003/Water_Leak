import {
  ApexAxisChartSeries,
  ApexChart,
  ApexXAxis,
  ApexTitleSubtitle,
  ApexStroke,
  ApexDataLabels,
  ApexTooltip,
  ApexYAxis
} from "ng-apexcharts";


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
  LOST_CONNECTION = 'lost_connection',
  NO_DATA = 'no_data'
}

export type ChartOptions = {
  series: ApexAxisChartSeries;
  chart: ApexChart;
  xaxis: ApexXAxis;
  yaxis: ApexYAxis;
  stroke: ApexStroke;
  tooltip: ApexTooltip;
  dataLabels: ApexDataLabels;
  title: ApexTitleSubtitle;
  markers?: any;
  colors?: string[];
};
