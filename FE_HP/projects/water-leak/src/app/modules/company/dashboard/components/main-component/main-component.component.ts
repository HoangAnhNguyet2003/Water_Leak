import { Component, inject, OnInit, signal, computed, effect, ViewChild } from '@angular/core';
import { Router } from '@angular/router';
import { DashboardMainServiceService } from '../../services/dashboard-main-service.service';
import { DashBoardData, DashBoardDataStatus, ChartOptions } from '../../models';
import { catchError } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChartDataService } from '../../../../../core/services/company/chart-data.service';
import { ClockServiceService } from '../../../water-clock/services/clock-service.service';
import { of } from 'rxjs';
import { NgApexchartsModule, ChartComponent } from "ng-apexcharts";


@Component({
  selector: 'app-main-component',
  standalone: true,
  imports: [CommonModule, FormsModule, NgApexchartsModule],
  templateUrl: './main-component.component.html',
  styleUrls: ['./main-component.component.scss']
})
export class MainComponentComponent implements OnInit {
  @ViewChild("chart") chart!: ChartComponent;
  public chartOptions = signal<ChartOptions>({
    series: [{ name: 'Lưu lượng', data: [] }],
    chart: { type: 'line', height: 350 },
    xaxis: {
      categories: [],
      labels: {
        maxHeight: undefined,
        rotate: -45,
        trim: false,
        hideOverlappingLabels: false,
        style: {
          colors: [],
          fontSize: '11px'
        }
      }
    },
    dataLabels: { enabled: false },
    stroke: { curve: 'smooth' },
    yaxis: { title: { text: 'Lưu lượng' } },
    tooltip: { x: { show: true } },
    title: { text: 'Lưu lượng theo thời gian', align: 'left' }
  });

  dashBoardService = inject(DashboardMainServiceService);
  router = inject(Router);
  private chartDataService = inject(ChartDataService);
  private clockService = inject(ClockServiceService);
  allData = signal<DashBoardData[]>([]);
  searchTerm = signal<string>('');

  chartState = this.chartDataService.getState();
  selectedMeterId = signal<number | null>(null);
  selectedMeterName = signal<string | null>(null);

  private readonly chartSyncEffect = effect(() => {
    const cd = this.chartState().chartData;
    if (!cd) return;

    const chartData = cd.data ?? [];
    const categories = chartData.map(d => d.timestamp);
    const lineSeries = chartData.map(d => d.value);
    const leakSeries = chartData.map(d => d.predictedLabel === 'leak' ? d.value : null);

  const series: any[] = [ { name: 'Lưu lượng', type: 'line', data: lineSeries } ];
  const activeType = this.chartState().activeChartType;
    const showAnomaly = activeType === 'anomaly' || activeType === 'anomaly-ai';
    if (showAnomaly && leakSeries.some(v => v !== null)) {
      series.push({ name: 'Leak', type: 'scatter', data: leakSeries, marker: { size: 8, fillColor: '#ff1744', strokeWidth: 1 } });
    }

    this.chartOptions.set({
      series,
      chart: { type: 'line', height: 350 },
      dataLabels: { enabled: false },
      stroke: { curve: 'smooth' },
      xaxis: {
        categories,
        labels: {
          maxHeight: undefined,
          rotate: -45,
          trim: false,
          hideOverlappingLabels: false,
          style: {
            colors: [],
            fontSize: '11px'
          }
        }
      },
      yaxis: { title: { text: 'Lưu lượng' } },
      tooltip: {
        shared: false,
        intersect: true,
        x: { show: true },
        y: {
          formatter: (val: any, opts: any) => {
            try {
              const idx = opts.dataPointIndex;
              const seriesName = opts?.w?.config?.series?.[opts.seriesIndex]?.name ?? '';
              const point = chartData[idx];
              if (point) {
                // single-line tooltip: show flow and indicate Leak when appropriate
                if (seriesName === 'Leak' || point.predictedLabel === 'leak') {
                  const conf = point.confidence !== undefined && point.confidence !== null ? ` (conf: ${point.confidence})` : '';
                  return `Lưu lượng: ${point.value} — Leak${conf}`;
                }
                return `Lưu lượng: ${point.value}`;
              }
            } catch (e) {}
            return val;
          }
        }
      },
      title: { text: `Lưu lượng tức thời - ${this.selectedMeterName() ?? ''}`, align: 'left' },
      markers: { size: 6 },
      colors: ['#4285f4', '#ff1744']
    });

    try {
      if (this.chart && this.chart.updateOptions) {
        // Use smooth animation and avoid redrawing paths unnecessarily
        this.chart.updateOptions(this.chartOptions(), false, true, true);
      }
    } catch (_e) {
      // ignore
    }
  }, { allowSignalWrites: true });

  totalNormalMeters = computed(() => {
    const arr = this.allData() ?? [];
    return arr.filter(item => item.status === DashBoardDataStatus.NORMAL).length;
  });

  totalAnomalies = computed(() => {
    const real = this.clockService.getAnomalyDetectedCount();
    if (real > 0) return real;
    const arr = this.allData() ?? [];
    return arr.filter(item => item.status === DashBoardDataStatus.ANOMALY).length;
  });

  filteredData = computed(() => {
    const searchLower = this.searchTerm().toLowerCase();
    let data = this.allData() ?? [];

    if (searchLower) {
      data = data.filter(item =>
        String(item.name).toLowerCase().includes(searchLower) ||
        String(item.branchName).toLowerCase().includes(searchLower)
      );
    }

    return data.sort((a, b) => {
      const statusPriority = {
        [DashBoardDataStatus.ANOMALY]: 0,
        [DashBoardDataStatus.NORMAL]: 1,
        [DashBoardDataStatus.LOST_CONNECTION]: 2,
        [DashBoardDataStatus.NO_DATA]: 3
      };

      const priorityA = statusPriority[a.status] ?? 999;
      const priorityB = statusPriority[b.status] ?? 999;

      if (priorityA !== priorityB) {
        return priorityA - priorityB;
      }

      return String(a.name).localeCompare(String(b.name));
    });
  });

  ngOnInit() {
    this.dashBoardService.getMeterData().pipe(
      catchError((err) => {
        console.error('Error fetching data', err);
        return of([]);
      })
    ).subscribe((data) => {
      this.allData.set(data);
      if (data && data.length > 0 && this.selectedMeterId() === null) {
        this.selectMeter(data[0]);
      }
    });

    this.chartOptions.set({
      series: [{ name: "Lưu lượng", data: [] }],
      chart: { type: "line", height: 350 },
      dataLabels: { enabled: false },
      stroke: { curve: "smooth" },
      xaxis: {
        categories: [],
        labels: {
          maxHeight: undefined,
          rotate: -45,
          trim: false,
          hideOverlappingLabels: false,
          style: {
            colors: [],
            fontSize: '11px'
          }
        }
      },
      yaxis: { title: { text: "Lưu lượng" } },
      tooltip: { x: { show: true } },
      title: { text: "Lưu lượng theo thời gian", align: "left" }
    });

  }

  onSearchChange(event: any) {
    this.searchTerm.set(event.target.value);
  }

  trackByFn(index: number, item: DashBoardData): string | number {
    return item.id;
  }

  switchChartTab(tab: 'general' | 'anomaly' | 'anomaly-ai') {
    this.chartDataService.changeChartType(tab);
  }

  isActiveTab(tab: 'general' | 'anomaly' | 'anomaly-ai'): boolean {
    return this.chartState().activeChartType === tab;
  }

  getStatusClass(status: DashBoardDataStatus): string {
    switch (status) {
      case DashBoardDataStatus.NORMAL: return 'status-normal';
      case DashBoardDataStatus.ANOMALY: return 'status-anomaly';
      case DashBoardDataStatus.LOST_CONNECTION: return 'status-lost-connection';
      case DashBoardDataStatus.NO_DATA: return 'status-no-data';
      default: return 'status-unknown';
    }
  }

  getStatusText(status: DashBoardDataStatus): string {
    switch (status) {
      case DashBoardDataStatus.NORMAL: return 'Bình thường';
      case DashBoardDataStatus.ANOMALY: return 'Bất thường';
      case DashBoardDataStatus.LOST_CONNECTION: return 'Mất kết nối';
      case DashBoardDataStatus.NO_DATA: return 'Không có dữ liệu';
      default: return 'Không xác định';
    }
  }

  async selectMeter(item: DashBoardData): Promise<void> {
    if (item.meter_data) {
      const meterId = item.meter_data.id; // keep original type (string or number)
      this.selectedMeterId.set(meterId as any);
      this.selectedMeterName.set(item.meter_data.name);
      await this.updateChartDataForMeter(item);
    }
  }

  isMeterSelected(item: DashBoardData): boolean {
    const meterId = item.meter_data?.id;
    return String(this.selectedMeterId()) === String(meterId);
  }

  private async updateChartDataForMeter(item: DashBoardData): Promise<void> {
    // Only call selectMeter, let chartSyncEffect handle the chart updates
    await this.chartDataService.selectMeter(item.meter_data.id as any, item.meter_data.name);
  }

  navigateToWaterClock(filterStatus: string): void {
    // Map status to appropriate filter value
    let statusFilter: string;
    switch (filterStatus) {
      case 'normal':
        statusFilter = 'normal';
        break;
      case 'anomaly':
        statusFilter = 'anomaly';
        break;
      default:
        statusFilter = 'all';
    }

    this.router.navigate(['/company/water-clock'], {
      queryParams: { statusFilter: statusFilter }
    });
  }
}
