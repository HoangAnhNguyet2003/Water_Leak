import { Component, OnInit, signal, computed, inject, ViewChild, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { Location } from '@angular/common';
import { PredictionData } from '../../models';
import { ChartDataService } from '../../../../../core/services/company/chart-data.service';
import { ChartDataPoint } from '../../../../../core/models/chart-data.interface';
import { NgApexchartsModule, ChartComponent } from 'ng-apexcharts';

@Component({
  selector: 'app-chart-view',
  standalone: true,
  imports: [CommonModule, NgApexchartsModule],
  templateUrl: './chart-view.component.html',
  styleUrls: ['./chart-view.component.scss']
})
export class ChartViewComponent implements OnInit {
  // Thông tin meter được truyền qua route params
  meterId = signal<string>('');
  meterName = signal<string>('Name');

  // Chart state management
  activeChartTab = signal<'general' | 'anomaly' | 'anomaly-ai'>('general');
  private chartDataService = inject(ChartDataService);
  private chartState = this.chartDataService.getState();

  showPredictionPopup = signal<boolean>(false);
  public chartLoaded = signal<boolean>(false);
  predictionData = signal<PredictionData[]>([
    { id: '1', thoi_gian: '**********', luu_luong: '**********', trang_thai: 'Bình thường' },
  ]);

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private location: Location
  ) {}

  @ViewChild('chart') chart!: ChartComponent;

  // Apex chart options (similar to main component)
    public chartOptions = signal<any>({
    series: [{ name: 'Lưu lượng', data: [] }],
    chart: { type: 'line', height: 350 },
    xaxis: { categories: [] },
    dataLabels: { enabled: false },
    stroke: { curve: 'smooth' },
    yaxis: { title: { text: 'Lưu lượng' } },
    tooltip: { x: { show: true } },
    title: { text: 'Lưu lượng theo thời gian', align: 'left' },
    markers: { size: 6 },
    colors: ['#4285f4', '#ff1744']
  });

  private readonly chartSyncEffect = effect(() => {
    const cd = this.chartState().chartData;
    if (!cd) return;
    const chartData = cd.data ?? [];
    const categories = chartData.map(d => d.timestamp);
    const lineSeries = chartData.map(d => d.value);
    const leakSeries = chartData.map(d => d.predictedLabel === 'leak' ? d.value : null);
  const series: any[] = [ { name: 'Lưu lượng', type: 'line', data: lineSeries } ];

  console.debug('[ChartView] activeType=', this.chartState().activeChartType, 'pointsSample=', chartData.slice(0,5));
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
      xaxis: { categories },
      yaxis: { title: { text: cd.config?.yAxisLabel ?? 'Lưu lượng' } },
      tooltip: {
        shared: false,   // ⬅ tắt tooltip chung
        intersect: true, // ⬅ chỉ hiển thị đúng điểm được hover
        x: { show: true },
        y: {
          formatter: (val: any, opts: any) => {
            try {
              const idx = opts.dataPointIndex;
              const seriesName = opts.w.config.series[opts.seriesIndex].name;
              const point = chartData[idx];
              if (point) {
                if (seriesName === 'Leak') {
                  const conf = point.confidence !== undefined ? ` (conf: ${point.confidence})` : '';
                  return `Lưu lượng: ${point.value} — Leak${conf}`;
                }
                return `Lưu lượng: ${point.value}`;
              }
            } catch (e) {}
            return val;
          }
        }
      },
      title: { text: `Lưu lượng - ${cd.meterName ?? this.meterName() ?? ''}`, align: 'left' },
      markers: { size: 6 },
      colors: ['#4285f4', '#ff1744']
    });

    try {
      this.chart?.updateOptions?.({ series: this.chartOptions().series, xaxis: this.chartOptions().xaxis }, false, true);
    } catch (e) {
    }
  }, { allowSignalWrites: true });

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.meterId.set(params['id']);
      }
      if (params['name']) {
        this.meterName.set(decodeURIComponent(params['name']));
      }

      if (this.meterId()) {
        const raw = this.meterId();
        const maybeNum = Number(raw);
        const idArg: number | string = Number.isFinite(maybeNum) && String(maybeNum) === String(raw) ? maybeNum : raw;
        void this.loadMeterById(idArg, this.meterName());
      }
    });
  }

  public async loadMeterById(id: number | string, name?: string | null): Promise<void> {
    try {
      await this.chartDataService.selectMeter(id as any, (name ?? '') as any);
    } catch (e) {
      console.error('[ChartView] failed to select meter', e);
      return;
    }

    const cd = this.chartState().chartData;
    const chartData = cd?.data ?? [];
    const meterNameFromState = cd?.meterName ?? name ?? this.meterName();
    this.meterName.set(meterNameFromState);

    this.chartOptions.set({
      series: [{ name: 'Lưu lượng', data: chartData.map(d => d.value) }],
      chart: { type: 'line', height: 350 },
      dataLabels: { enabled: false },
      stroke: { curve: 'smooth' },
      xaxis: { categories: chartData.map(d => d.timestamp) },
      yaxis: { title: { text: 'Lưu lượng' } },
      tooltip: { x: { show: true } },
      title: { text: `Lưu lượng - ${meterNameFromState ?? ''}`, align: 'left' },
      markers: { size: 6 },
      colors: ['#4285f4', '#e53935']
    });

    this.chartLoaded.set((chartData?.length ?? 0) > 0);

    try {
      this.chart?.updateOptions?.({ series: this.chartOptions().series, xaxis: this.chartOptions().xaxis }, false, true);
    } catch (e) {
      // ignore
    }
  }

  public dataPoints = computed<ChartDataPoint[]>(() => this.chartState().chartData?.data ?? []);

  public anomalyPoints = computed(() => {
    return this.dataPoints().filter(p => !!p.isAnomaly).map(p => ({ timestamp: p.timestamp, value: p.value }));
  });

  // log and set a debug flag when chart data arrives
  private readonly _debugEffect = effect(() => {
    const cd = this.chartState().chartData;
    if (!cd) {
      this.chartLoaded.set(false);
      return;
    }
    const len = cd.data?.length ?? 0;
    // set loaded when we have any points
    this.chartLoaded.set(len > 0);
    // console debug to help diagnose missing data at runtime
    // eslint-disable-next-line no-console
    console.debug('[ChartView] chartData arrived:', { meterId: cd.meterId, points: len });
  }, { allowSignalWrites: true });



  // Chart data cho từng tab (sử dụng dữ liệu từ dashboard)
  generalChartData = computed(() => ({
    title: 'Tổng quát',
    subtitle: 'General Flow Analysis',
  }));

  anomalyChartData = computed(() => ({
    title: 'Hiển thị bất thường',
    subtitle: 'Anomaly Detection',
  }));

  anomalyAiChartData = computed(() => ({
    title: 'Hiển thị bất thường - AI',
    subtitle: 'AI-Enhanced Anomaly Detection',
  }));

  currentChartData = computed(() => {
    switch (this.activeChartTab()) {
      case 'anomaly':
        return this.anomalyChartData();
      case 'anomaly-ai':
        return this.anomalyAiChartData();
      default:
        return this.generalChartData();
    }
  });

  public headerTitle = computed(() => {
    const cd = this.chartState().chartData;
    if (cd?.meterName) return cd.meterName;
    if (this.meterName()) return this.meterName();
    return this.currentChartData().title;
  });

  // Navigation methods
  goBack(): void {
    this.location.back();
  }

  setActiveTab(tab: 'general' | 'anomaly' | 'anomaly-ai'): void {
    this.activeChartTab.set(tab);
    void this.chartDataService.changeChartType(tab);
  }



  shouldShowPredictionButton(): boolean {
    return this.activeChartTab() === 'anomaly' || this.activeChartTab() === 'anomaly-ai';
  }

  // Toggle prediction popup
  togglePredictionPopup(): void {
    this.showPredictionPopup.set(!this.showPredictionPopup());
  }

  // Close prediction popup
  closePredictionPopup(): void {
    this.showPredictionPopup.set(false);
  }

  // TrackBy function for prediction data
  trackByPredictionId(index: number, item: PredictionData): string {
    return item.id;
  }
}
