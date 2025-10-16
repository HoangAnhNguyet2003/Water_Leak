import { Component, inject, OnInit, signal, computed, effect, ViewChild } from '@angular/core';
import { Router } from '@angular/router';
import { DashboardMainServiceService } from '../../services/dashboard-main-service.service';
import { DashBoardData, DashBoardDataStatus, ChartOptions } from '../../models';
import { catchError } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChartDataService } from '../../../../../core/services/company/chart-data.service';
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
    xaxis: { categories: [] },
    dataLabels: { enabled: false },
    stroke: { curve: 'smooth' },
    yaxis: { title: { text: 'Lưu lượng' } },
    tooltip: { x: { show: true } },
    title: { text: 'Lưu lượng theo thời gian', align: 'left' }
  });

  dashBoardService = inject(DashboardMainServiceService);
  router = inject(Router);
  private chartDataService = inject(ChartDataService);
  allData = signal<DashBoardData[]>([]);
  searchTerm = signal<string>('');

  chartState = this.chartDataService.getState();
  selectedMeterId = signal<number | null>(null);
  selectedMeterName = signal<string | null>(null);

  private readonly chartSyncEffect = effect(() => {
    const cd = this.chartState().chartData;
    const activeType = this.chartState().activeChartType; // Đảm bảo effect trigger khi tab thay đổi
    if (!cd) return;

    const chartData = cd.data ?? [];

    this.markExtendedLeakPoints(chartData);

    const categories = chartData.map(d => d.timestamp);
    const lineSeries = chartData.map(d => d.value);

    if (cd.meterName) {
      this.selectedMeterName.set(cd.meterName);
    }

    const series: any[] = [ { name: 'Lưu lượng', type: 'line', data: lineSeries } ];

    if (activeType === 'anomaly-ai') {
      const leakSeries = chartData.map(d =>
        d.predictedLabel === 'leak' ? d.value : null
      );
      if (leakSeries.some((v: number | null) => v !== null)) {
        series.push({
          name: 'Rò rỉ (AI)',
          type: 'scatter',
          data: leakSeries,
          marker: {
            size: 6,
            fillColor: '#ff1744',
            strokeWidth: 1,
            strokeColor: '#ffffff'
          }
        });
      }
    } else if (activeType === 'anomaly') {
      const thresholdAnomalySeries = chartData.map(d =>
        (d.isAnomaly && d.predictedLabel !== 'leak') ? d.value : null
      );
      if (thresholdAnomalySeries.some((v: number | null) => v !== null)) {
        series.push({
          name: 'Bất thường (Ngưỡng)',
          type: 'scatter',
          data: thresholdAnomalySeries,
          marker: {
            size: 8,
            fillColor: '#ff9800',
            strokeWidth: 1,
            strokeColor: '#ffffff'
          }
        });
      }
    }

    this.chartOptions.set({
      series,
      chart: { type: 'line', height: 350 },
      dataLabels: { enabled: false },
      stroke: { curve: 'smooth' },
      xaxis: {
        categories,
        labels: {
          rotate: -45,
          rotateAlways: true,
          hideOverlappingLabels: false,
          trim: false,
          maxHeight: 120,
          style: { 
            fontSize: '11px',
            fontFamily: 'Arial, sans-serif'
          }
        },
        tickAmount: Math.min(10, Math.floor(categories.length / 2))
      },
      yaxis: { title: { text: 'Lưu lượng' } },
      tooltip: {
        shared: false,
        intersect: true,
        x: { show: true },
        y: {
          formatter: (val: any, opts: any) => {
            const idx = opts.dataPointIndex;
            const seriesName = opts?.w?.config?.series?.[opts.seriesIndex]?.name ?? '';
            const point = chartData[idx];
            if (point) {
              if (seriesName === 'Rò rỉ (AI)') {
                const conf = point.confidence ? ` (tin cậy: ${point.confidence})` : '';
                return `Lưu lượng: ${point.value} — Rò rỉ LSTM-AE${conf}`;
              }
              if (seriesName === 'Bất thường (Ngưỡng)') {
                return `Lưu lượng: ${point.value} — Bất thường theo ngưỡng`;
              }
              return `Lưu lượng: ${point.value}`;
            }
            return val;
          }
        }
      },
      title: { text: `Lưu lượng tức thời - ${this.selectedMeterName() ?? ''}`, align: 'left' },
      markers: { size: 6 },
      colors: ['#4285f4', '#ff1744', '#ff9800']
    });

    this.chart?.updateOptions?.(this.chartOptions(), false, true, true);
  }, { allowSignalWrites: true });

  totalNormalMeters = computed(() => {
    const arr = this.allData() ?? [];
    return arr.filter(item => item.status === DashBoardDataStatus.NORMAL).length;
  });

  totalAnomalies = computed(() => {
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
    // Reset chart type về 'general' và clear selection để đảm bảo fresh state
    this.chartDataService.resetChartType();
    this.selectedMeterId.set(null);
    this.selectedMeterName.set(null);
    
    this.dashBoardService.getMeterData().pipe(
      catchError(() => of([]))
    ).subscribe((data) => {
      this.allData.set(data);
      if (data?.length > 0 && !this.selectedMeterId()) {
        this.selectMeter(data[0]);
      }
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
    const statusMap: { [key: string]: string } = { 'normal': 'normal', 'anomaly': 'anomaly' };
    this.router.navigate(['/company/water-clock'], {
      queryParams: { statusFilter: statusMap[filterStatus] || 'all' }
    });
  }

  private markExtendedLeakPoints(chartData: any[]): void {
    if (chartData.length === 0) return;

    const originalLabels = chartData.map(point => ({
      originalLabel: point.predictedLabel,
      originalAnomaly: point.isAnomaly
    }));

    const leakIndices: number[] = [];
    chartData.forEach((point, index) => {
      if (originalLabels[index].originalLabel === 'leak' && originalLabels[index].originalAnomaly) {
        leakIndices.push(index);
      }
    });

    if (leakIndices.length === 0) return;

    let pointsPerHour = 12;
    if (chartData.length >= 2) {
      const firstTime = new Date(chartData[0].timestamp);
      const secondTime = new Date(chartData[1].timestamp);
      const timeDiffMinutes = (secondTime.getTime() - firstTime.getTime()) / (1000 * 60);
      if (timeDiffMinutes > 0) {
        pointsPerHour = Math.ceil(60 / timeDiffMinutes);
      }
    }

    const processedIndices = new Set<number>();
    
    leakIndices.forEach(leakIndex => {
      if (processedIndices.has(leakIndex)) return;
      
      const extendPoints = Math.min(Math.floor(pointsPerHour / 2), chartData.length - leakIndex);
      for (let i = leakIndex; i < leakIndex + extendPoints && i < chartData.length; i++) {
        if (!processedIndices.has(i)) {
          chartData[i].predictedLabel = 'leak';
          processedIndices.add(i);
        }
      }
    });
  }
}
