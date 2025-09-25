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
    // build anomaly scatter series: plot value where isAnomaly true, else null to keep positions
    const anomalySeries = chartData.map(d => d.isAnomaly ? d.value : null);

    const series: any[] = [
      { name: 'Lưu lượng', type: 'line', data: lineSeries },
    ];
    // add anomaly series as scatter with red markers if any anomalies exist
    if (anomalySeries.some(v => v !== null)) {
      series.push({ name: 'Bất thường', type: 'scatter', data: anomalySeries });
    }

    this.chartOptions.set({
      series,
      chart: { type: 'line', height: 350 },
      dataLabels: { enabled: false },
      stroke: { curve: 'smooth' },
      xaxis: { categories },
      yaxis: { title: { text: 'Lưu lượng' } },
      tooltip: { x: { show: true } },
      title: { text: `Lưu lượng tức thời - ${this.selectedMeterName() ?? ''}`, align: 'left' },
      markers: { size: 6 },
      colors: ['#4285f4', '#e53935']
    });

    try {
      this.chart?.updateOptions?.({ series: this.chartOptions().series, xaxis: this.chartOptions().xaxis }, false, true);
    } catch (_e) {
      // ignore
    }
  });

  totalAnomalies = computed(() => {
    const real = this.clockService.getAnomalyDetectedCount();
    if (real > 0) return real;
    const arr = this.allData() ?? [];
    return arr.filter(item => item.status === DashBoardDataStatus.ANOMALY).length;
  });

  totalVerifiedAnomalies = computed(() => {
    const real = this.clockService.getOnFixingCount();
    if (real > 0) return real;
    const arr = this.allData() ?? [];
    return arr.filter(item => item.status === DashBoardDataStatus.ANOMALY).length;
  });

  filteredData = computed(() => {
    const searchLower = this.searchTerm().toLowerCase();
    if (!searchLower) return this.allData();
    return this.allData().filter(item =>
      String(item.name).toLowerCase().includes(searchLower) ||
      String(item.branchName).toLowerCase().includes(searchLower)
    );
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
      xaxis: { categories: [] },
      yaxis: { title: { text: "Lưu lượng" } },
      tooltip: { x: { show: true } },
      title: { text: "Lưu lượng theo thời gian", align: "left" }
    });

    effect(() => {
      const cd = this.chartState().chartData;
      if (!cd) return;
      const chartData = cd.data ?? [];
      const categories = chartData.map(d => d.timestamp);
      const lineSeries = chartData.map(d => d.value);
      const anomalySeries = chartData.map(d => d.isAnomaly ? d.value : null);

      const series: any[] = [ { name: 'Lưu lượng', type: 'line', data: lineSeries } ];
      if (anomalySeries.some(v => v !== null)) {
        series.push({ name: 'Bất thường', type: 'scatter', data: anomalySeries });
      }

      this.chartOptions.set({
        series,
        chart: { type: 'line', height: 350 },
        dataLabels: { enabled: false },
        stroke: { curve: 'smooth' },
        xaxis: { categories },
        yaxis: { title: { text: 'Lưu lượng' } },
        tooltip: { x: { show: true } },
        title: { text: `Lưu lượng tức thời - ${this.selectedMeterName() ?? ''}`, align: 'left' },
        markers: { size: 6 },
        colors: ['#4285f4', '#e53935']
      });
      try {
        this.chart?.updateOptions?.({ series: this.chartOptions().series, xaxis: this.chartOptions().xaxis }, false, true);
      } catch (e) {
        // ignore
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
      default: return 'status-unknown';
    }
  }

  getStatusText(status: DashBoardDataStatus): string {
    switch (status) {
      case DashBoardDataStatus.NORMAL: return 'Bình thường';
      case DashBoardDataStatus.ANOMALY: return 'Bất thường';
      case DashBoardDataStatus.LOST_CONNECTION: return 'Mất kết nối';
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
  await this.chartDataService.selectMeter(item.meter_data.id as any, item.meter_data.name);

    const chartData = this.chartState().chartData?.data ?? [];
    this.chartOptions.set({
      series: [{ name: 'Lưu lượng', data: chartData.map(d => d.value) }],
      chart: { type: 'line', height: 350 },
      dataLabels: { enabled: false },
      stroke: { curve: 'smooth' },
      xaxis: { categories: chartData.map(d => d.timestamp) },
      yaxis: { title: { text: 'Lưu lượng' } },
      tooltip: { x: { show: true } },
      title: { text: `Lưu lượng - ${item.meter_data.name}`, align: 'left' }
    });
    // Trigger chart update if the chart component is available
    try {
      this.chart?.updateOptions?.({
        series: this.chartOptions().series,
        xaxis: this.chartOptions().xaxis
      }, false, true);
    } catch (e) {
      // ignore - updateOptions may not be available immediately
    }
  }

  navigateToWaterClock(filterStatus: string): void {
    this.router.navigate(['/company/water-clock'], {
      queryParams: { statusFilter: filterStatus }
    });
  }
}
