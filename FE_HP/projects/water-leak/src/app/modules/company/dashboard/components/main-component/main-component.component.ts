import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { DashboardMainServiceService } from '../../services/dashboard-main-service.service';
import { DashBoardData, DashBoardDataStatus } from '../../models';
import { catchError } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChartDataService } from '../../../../../core/services/company/chart-data.service';
import { ClockServiceService } from '../../../water-clock/services/clock-service.service';
import { of } from 'rxjs';

@Component({
  selector: 'app-main-component',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './main-component.component.html',
  styleUrls: ['./main-component.component.scss']
})
export class MainComponentComponent implements OnInit {
  dashBoardService = inject(DashboardMainServiceService);
  router = inject(Router);
  private chartDataService = inject(ChartDataService);
  private clockService = inject(ClockServiceService);
  allData = signal<DashBoardData[]>([]);
  searchTerm = signal<string>('');

  // Chart state management
  chartState = this.chartDataService.getState();
  selectedMeterId = signal<number | null>(null);
  selectedMeterName = signal<string | null>(null);

  totalAnomalies = computed(() => {
    const real = this.clockService.getAnomalyDetectedCount();
    if (real > 0) return real;
    
    // Giả sử bạn muốn đếm số lượng bất thường dựa trên status
    return this.allData().filter(item => item.status === DashBoardDataStatus.ANOMALY).length;
  });

  totalVerifiedAnomalies = computed(() => {
    const real = this.clockService.getOnFixingCount();
    if (real > 0) return real;
    
    // Tương tự như trên, bạn có thể kiểm tra trạng thái hoặc thuộc tính khác
    return this.allData().filter(item => item.status === DashBoardDataStatus.ANOMALY).length;
  });

  filteredData = computed(() => {
    const searchLower = this.searchTerm().toLowerCase();
    if (!searchLower) return this.allData();

    return this.allData().filter(item =>
      // Chuyển đổi item.name và item.branchName thành chuỗi trước khi gọi toLowerCase
      String(item.name).toLowerCase().includes(searchLower) ||
      String(item.branchName).toLowerCase().includes(searchLower)
    );
  });

  // Current chart data
  currentChartData = computed(() => this.chartState().chartData);

  ngOnInit() {
  this.dashBoardService.getMeterData().pipe(
    catchError((err) => {
      console.error('Error fetching data', err);
      return of([]); 
    })
  ).subscribe((data) => {
    this.allData.set(data); 
  });
}

  onSearchChange(event: any) {
    this.searchTerm.set(event.target.value);
  }

  getStatusLabel(status: DashBoardDataStatus): string {
    switch (status) {
      case DashBoardDataStatus.NORMAL:
        return 'Hoạt động';
      case DashBoardDataStatus.ANOMALY:
        return 'Bất thường';
      case DashBoardDataStatus.LOST_CONNECTION:
        return 'Lỗi';
      default:
        return 'Không xác định';
    }
  }



  trackByFn(index: number, item: DashBoardData): string | number {
    return item.id; // Sử dụng thuộc tính id duy nhất cho mỗi mục
  }


  // Chart tab methods
  switchChartTab(tab: 'general' | 'anomaly' | 'anomaly-ai') {
    this.chartDataService.changeChartType(tab);
  }

  isActiveTab(tab: 'general' | 'anomaly' | 'anomaly-ai'): boolean {
    return this.chartState().activeChartType === tab;
  }
  getStatusClass(status: DashBoardDataStatus): string {
    switch (status) {
      case DashBoardDataStatus.NORMAL:
        return 'status-normal';
      case DashBoardDataStatus.ANOMALY:
        return 'status-anomaly';
      case DashBoardDataStatus.LOST_CONNECTION:
        return 'status-lost-connection';
      default:
        return '';
    }
  }

  getStatusText(status: DashBoardDataStatus): string {
    switch (status) {
      case DashBoardDataStatus.NORMAL:
        return 'Bình thường';
      case DashBoardDataStatus.ANOMALY:
        return 'Bất thường';
      case DashBoardDataStatus.LOST_CONNECTION:
        return 'Mất kết nối';
      default:
        return 'Không xác định';
    }
  }
  // Meter selection
selectMeter(item: DashBoardData): void {
  if (item.meter_data) {
    // Chuyển đổi id thành number nếu cần
    const meterId = typeof item.meter_data.id === 'string' ? Number(item.meter_data.id) : item.meter_data.id;

    this.selectedMeterId.set(meterId); // Cập nhật trạm được chọn
    this.selectedMeterName.set(item.meter_data.name);

    // Tạo dữ liệu mới cho trạm được chọn
    this.updateChartDataForMeter(item);
    } else {
      console.warn('Meter data is not available for the selected item.');
    }
  }

  // Kiểm tra trạm đang được chọn
  isMeterSelected(item: DashBoardData): boolean {
    const meterId = typeof item.meter_data?.id === 'string' ? Number(item.meter_data.id) : item.meter_data?.id;
    return this.selectedMeterId() === meterId;
  }

  // Cập nhật dữ liệu biểu đồ cho trạm được chọn
  private updateChartDataForMeter(item: DashBoardData): void {
    if (item.meter_data) {
      const meterId = typeof item.meter_data.id === 'string' ? Number(item.meter_data.id) : item.meter_data.id;
      this.chartDataService.selectMeter(meterId, item.meter_data.name);
    } else {
      console.warn('Meter data is not available for the selected item.');
    }
  }

  // Không cần tự tạo points — dùng service chung

  // Helper để vẽ SVG (dùng trong template)
  getPolylinePoints(data: Array<{ timestamp: string; value: number; predictedValue?: number }>, key: 'value' | 'predictedValue'): string {
    if (!data || data.length === 0) return '';
    return data.map((point, index) => {
      const x = this.getXCoordinate(index, data.length);
      const raw = key === 'value' ? point.value : (point.predictedValue ?? point.value);
      const y = this.getYCoordinate(raw);
      return `${x},${y}`;
    }).join(' ');
  }

  getXAxisLabels(data: Array<{ timestamp: string }>): string[] {
    if (!data || data.length === 0) return [];
    const totalLabels = 7;
    const step = Math.max(1, Math.floor(data.length / totalLabels));
    const labels: string[] = [];
    for (let i = 0; i < data.length; i += step) {
      labels.push(data[i].timestamp);
    }
    if (labels[labels.length - 1] !== data[data.length - 1].timestamp) {
      labels[labels.length - 1] = data[data.length - 1].timestamp;
    }
    return labels;
  }

  private getXCoordinate(index: number, totalPoints: number): number {
    const chartWidth = 800;
    const margin = 70;
    if (totalPoints <= 1) return margin;
    const step = chartWidth / (totalPoints - 1);
    return margin + (index * step);
  }

  private getYCoordinate(value: number): number {
    const chartHeight = 280;
    const margin = 30;
    const maxValue = 40;
    const clamped = Math.max(0, Math.min(maxValue, value));
    const scale = chartHeight / maxValue;
    return margin + (chartHeight - (clamped * scale));
  }

  // Điều hướng đến trang thông tin đồng hồ với bộ lọc
  navigateToWaterClock(filterStatus: string): void {
    this.router.navigate(['/company/water-clock'], {
      queryParams: { statusFilter: filterStatus }
    });
  }
}
