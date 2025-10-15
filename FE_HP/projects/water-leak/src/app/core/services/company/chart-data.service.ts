import { Injectable, signal } from '@angular/core';
import { ChartData, ChartState, ChartType } from './../../models/chart-data.interface';
import { ChartApiService } from './chart-api.service';
import { firstValueFrom } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ChartDataService {
  private state = signal<ChartState>({
    selectedMeterId: null,
    selectedMeterName: null,
    activeChartType: 'general',
    chartData: null
  });

  constructor(private chartApi: ChartApiService) {}

  private getSubtitleByType(type: ChartType): string {
    switch (type) {
      case 'anomaly':
        return 'Phân tích bất thường dựa trên ngưỡng';
      case 'anomaly-ai':
        return 'Phân tích bất thường sử dụng AI';
      default:
        return 'Theo dõi lưu lượng thời gian thực';
    }
  }

  private getLegendByType(type: ChartType): { label: string; color: string }[] {
    switch (type) {
      case 'anomaly':
        return [
          { label: 'Lưu lượng thực tế', color: '#4285f4' },
          { label: 'Ngưỡng dự đoán', color: '#34a853' }
        ];
      case 'anomaly-ai':
        return [
          { label: 'Lưu lượng thực tế', color: '#4285f4' },
          { label: 'Dự đoán AI', color: '#fbbc05' }
        ];
      default:
        return [
          { label: 'Lưu lượng thực tế', color: '#4285f4' },
          { label: 'Lưu lượng trung bình', color: '#34a853' }
        ];
    }
  }

  public async selectMeter(meterId: number, meterName: string): Promise<void> {
    const chartData = await firstValueFrom(this.chartApi.getInstantFlowRange(meterId, 4));
    this.state.update(state => ({
      ...state,
      selectedMeterId: meterId,
      selectedMeterName: chartData?.meterName ?? meterName,
      chartData
    }));
  }

  public async changeChartType(type: ChartType): Promise<void> {
    const currentState = this.state();
    if (!currentState.selectedMeterId || !currentState.selectedMeterName) {
      this.state.update(s => ({ ...s, activeChartType: type }));
      return;
    }
    // For anomaly tabs, call the predictions-aware endpoint so we get isAnomaly/confidence
    const chartData: ChartData = (type === 'anomaly' || type === 'anomaly-ai')
      ? await firstValueFrom(this.chartApi.getInstantFlowRangeWithPredictions(currentState.selectedMeterId!, 4))
      : await firstValueFrom(this.chartApi.getInstantFlowRange(currentState.selectedMeterId!, 4));

    this.state.update(state => ({
      ...state,
      activeChartType: type,
      chartData
    }));
  }

  // Getters
  public getState(): ReturnType<typeof signal<ChartState>> {
    return this.state;
  }
}
