import { Component, OnInit, signal, computed, inject, ViewChild, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { Location } from '@angular/common';
import { PredictionData } from '../../models';
import { ChartDataService } from '../../../../../core/services/company/chart-data.service';
import { ChartDataPoint } from '../../../../../core/models/chart-data.interface';
import { NgApexchartsModule, ChartComponent } from 'ng-apexcharts';
import { PredictiveModelService } from '../../../../branches/predictive-model/services/predictive-model.service';

@Component({
  selector: 'app-chart-view',
  standalone: true,
  imports: [CommonModule, NgApexchartsModule],
  templateUrl: './chart-view.component.html',
  styleUrls: ['./chart-view.component.scss']
})
export class ChartViewComponent implements OnInit {
  meterId = signal<string>('');
  meterName = signal<string>('Name');
  activeChartTab = signal<'general' | 'anomaly' | 'anomaly-ai'>('general');
  private chartDataService = inject(ChartDataService);
  private chartState = this.chartDataService.getState();

  showPredictionPopup = signal<boolean>(false);
  public chartLoaded = signal<boolean>(false);
  predictionData = signal<PredictionData[]>([]);
  isLoadingPredictions = signal<boolean>(false);

  sortedPredictionData = computed(() => {
    const data = this.predictionData();
    if (data.length === 0) return data;

    return [...data].sort((a, b) => {
      if (a.id === 'no_data' || a.id === 'error') return 1;
      if (b.id === 'no_data' || b.id === 'error') return -1;

      const timeA = this.parseFormattedTime(a.thoi_gian);
      const timeB = this.parseFormattedTime(b.thoi_gian);
      return timeB - timeA;
    });
  });

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private location: Location,
    private predictiveService: PredictiveModelService
  ) {}

  @ViewChild('chart') chart!: ChartComponent;

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
    this.markExtendedLeakPoints(chartData);

    const categories = chartData.map(d => d.timestamp);
    const lineSeries = chartData.map(d => d.value);
    const series: any[] = [{ name: 'Lưu lượng', type: 'line', data: lineSeries }];
    const activeType = this.chartState().activeChartType;

    if (activeType === 'anomaly-ai') {
      const leakSeries = chartData.map(d => d.predictedLabel === 'leak' ? d.value : null);
      if (leakSeries.some((v: number | null) => v !== null)) {
        series.push({
          name: 'Rò rỉ (AI)',
          type: 'scatter',
          data: leakSeries,
          marker: { size: 8, fillColor: '#ff1744', strokeWidth: 1, strokeColor: '#ffffff' }
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
          marker: { size: 8, fillColor: '#ff9800', strokeWidth: 1, strokeColor: '#ffffff' }
        });
      }
    }    this.chartOptions.set({
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
      yaxis: { title: { text: cd.config?.yAxisLabel ?? 'Lưu lượng' } },
      tooltip: {
        shared: false,
        intersect: true,
        x: { show: true },
        y: {
          formatter: (val: any, opts: any) => {
            try {
              const idx = opts.dataPointIndex;
              const seriesName = opts.w.config.series[opts.seriesIndex].name;
              const point = chartData[idx];
              if (point) {
                if (seriesName === 'Rò rỉ (AI)') {
                  const conf = point.confidence !== undefined ? ` (tin cậy: ${point.confidence})` : '';
                  return `Lưu lượng: ${point.value} — Rò rỉ LSTM-AE${conf}`;
                }
                if (seriesName === 'Bất thường (Ngưỡng)') {
                  return `Lưu lượng: ${point.value} — Bất thường theo ngưỡng`;
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
      colors: ['#4285f4', '#ff1744', '#ff9800']
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
    await this.chartDataService.selectMeter(id as any, (name ?? '') as any);
    const cd = this.chartState().chartData;
    const chartData = cd?.data ?? [];
    const meterNameFromState = cd?.meterName ?? name ?? this.meterName();
    this.meterName.set(meterNameFromState);
    this.chartLoaded.set(chartData.length > 0);
  }

  public dataPoints = computed<ChartDataPoint[]>(() => this.chartState().chartData?.data ?? []);

  public anomalyPoints = computed(() => {
    return this.dataPoints().filter(p => !!p.isAnomaly).map(p => ({ timestamp: p.timestamp, value: p.value }));
  });

  private readonly _debugEffect = effect(() => {
    const cd = this.chartState().chartData;
    if (!cd) {
      this.chartLoaded.set(false);
      return;
    }
    this.chartLoaded.set((cd.data?.length ?? 0) > 0);
  }, { allowSignalWrites: true });



  generalChartData = computed(() => ({ title: 'Tổng quát', subtitle: 'General Flow Analysis' }));
  anomalyChartData = computed(() => ({ title: 'Hiển thị bất thường', subtitle: 'Anomaly Detection' }));
  anomalyAiChartData = computed(() => ({ title: 'Hiển thị bất thường - AI', subtitle: 'AI-Enhanced Anomaly Detection' }));

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
  togglePredictionPopup(): void {
    const isOpening = !this.showPredictionPopup();
    this.showPredictionPopup.set(isOpening);

    if (isOpening && this.meterId()) {
      this.loadPredictionData();
    }
  }


  private loadPredictionData(): void {
    const meterId = this.meterId();
    if (!meterId) return;

    this.isLoadingPredictions.set(true);

    Promise.all([
      this.predictiveService.getLSTMAutoencoderPredictions(meterId).toPromise(),
      this.predictiveService.getLSTMPredictions(meterId).toPromise()
    ]).then(([lstmAutoencoder, lstmPredictions]) => {
      const allPredictions: PredictionData[] = [];

      const tempPredictions: any[] = [];

      if (lstmAutoencoder?.length) {
        lstmAutoencoder.forEach((pred, index) => {
          const rawTime = pred.prediction_time;
          const predTime = this.formatPredictionTime(rawTime);
          const flow = this.formatFlowValue(pred.recorded_instant_flow);
          const status = this.formatPredictionStatus(pred.predicted_label, pred.confidence);

          tempPredictions.push({
            id: `ae_${index}`,
            thoi_gian: predTime,
            luu_luong: flow,
            trang_thai: `[LSTM-AE] ${status}`,
            raw_time: rawTime
          });
        });
      }

      if (lstmPredictions?.length) {
        lstmPredictions.forEach((pred, index) => {
          const rawTime = pred.prediction_time;
          const predTime = this.formatPredictionTime(rawTime);
          const flow = this.formatFlowValue(pred.recorded_instant_flow);
          const status = this.formatPredictionStatus(pred.predicted_label, pred.confidence);

          tempPredictions.push({
            id: `lstm_${index}`,
            thoi_gian: predTime,
            luu_luong: flow,
            trang_thai: `[LSTM] ${status}`,
            raw_time: rawTime
          });
        });
      }

      tempPredictions.sort((a, b) => {
        const timeA = this.parseRawTime(a.raw_time);
        const timeB = this.parseRawTime(b.raw_time);
        return timeB - timeA;
      });

      tempPredictions.forEach(temp => {
        allPredictions.push({
          id: temp.id,
          thoi_gian: temp.thoi_gian,
          luu_luong: temp.luu_luong,
          trang_thai: temp.trang_thai
        });
      });

      this.predictionData.set(allPredictions.length > 0 ? allPredictions : [
        { id: 'no_data', thoi_gian: 'Không có dữ liệu', luu_luong: 'N/A', trang_thai: 'Chưa có dự đoán' }
      ]);

    }).catch(error => {
      this.predictionData.set([
        { id: 'error', thoi_gian: 'Lỗi tải dữ liệu', luu_luong: 'N/A', trang_thai: 'Không thể tải dự đoán' }
      ]);
    }).finally(() => {
      this.isLoadingPredictions.set(false);
    });
  }

  private parseRawTime(predTime: any): number {
    try {
      let date: Date;
      if (typeof predTime === 'string') {
        date = new Date(predTime);
      } else if (predTime && predTime.$date) {
        date = new Date(predTime.$date);
      } else if (predTime instanceof Date) {
        date = predTime;
      } else {
        return 0; // Invalid date gets lowest priority
      }

      if (isNaN(date.getTime())) return 0;
      return date.getTime();
    } catch (error) {
      return 0;
    }
  }

  private parseFormattedTime(timeStr: string): number {
    try {
      // Parse format: "dd/mm/yyyy hh:mm"
      if (timeStr === 'Invalid date' || timeStr === 'Không có dữ liệu' || timeStr === 'Lỗi tải dữ liệu') {
        return 0;
      }

      const parts = timeStr.split(' ');
      if (parts.length !== 2) return 0;

      const datePart = parts[0]; // dd/mm/yyyy
      const timePart = parts[1]; // hh:mm

      const dateComponents = datePart.split('/');
      const timeComponents = timePart.split(':');

      if (dateComponents.length !== 3 || timeComponents.length !== 2) return 0;

      const day = parseInt(dateComponents[0], 10);
      const month = parseInt(dateComponents[1], 10) - 1; // Month is 0-indexed
      const year = parseInt(dateComponents[2], 10);
      const hours = parseInt(timeComponents[0], 10);
      const minutes = parseInt(timeComponents[1], 10);

      const date = new Date(year, month, day, hours, minutes);
      return date.getTime();
    } catch (error) {
      return 0;
    }
  }

  private formatPredictionTime(predTime: any): string {
    try {
      let date: Date;
      if (typeof predTime === 'string') {
        date = new Date(predTime);
      } else if (predTime && predTime.$date) {
        date = new Date(predTime.$date);
      } else if (predTime instanceof Date) {
        date = predTime;
      } else {
        return 'Invalid date';
      }

      if (isNaN(date.getTime())) return 'Invalid date';

      const day = date.getUTCDate().toString().padStart(2, '0');
      const month = (date.getUTCMonth() + 1).toString().padStart(2, '0');
      const year = date.getUTCFullYear();
      const hours = date.getUTCHours().toString().padStart(2, '0');
      const minutes = date.getUTCMinutes().toString().padStart(2, '0');

      return `${day}/${month}/${year} ${hours}:${minutes}`;
    } catch (error) {
      return 'Invalid date';
    }
  }

  private formatFlowValue(flow: any): string {
    if (flow === null || flow === undefined || flow === '') return 'N/A';

    const numValue = parseFloat(flow);
    if (isNaN(numValue)) return 'N/A';

    return numValue.toFixed(2);
  }

  private formatPredictionStatus(label: string, confidence: any): string {
    if (label === 'normal') return 'Bình thường';
    if (label === 'leak') {
      if (confidence === 'NNcao') return 'Rò rỉ nghi ngờ cao';
      if (confidence === 'NNTB') return 'Rò rỉ nghi ngờ trung bình';
      if (confidence === 'NNthap') return 'Rò rỉ nghi ngờ thấp';
      return 'Rò rỉ';
    }
    return 'Không xác định';
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

    let pointsPerHour = 12; // Default fallback
    if (chartData.length >= 2) {
      try {
        const firstTime = new Date(chartData[0].timestamp);
        const secondTime = new Date(chartData[1].timestamp);
        const timeDiffMinutes = (secondTime.getTime() - firstTime.getTime()) / (1000 * 60);

        if (timeDiffMinutes > 0) {
          pointsPerHour = Math.ceil(60 / timeDiffMinutes);
        }
      } catch (e) {
        pointsPerHour = 12;
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

  closePredictionPopup(): void {
    this.showPredictionPopup.set(false);
  }

  trackByPredictionId(index: number, item: PredictionData): string {
    return item.id;
  }
}
