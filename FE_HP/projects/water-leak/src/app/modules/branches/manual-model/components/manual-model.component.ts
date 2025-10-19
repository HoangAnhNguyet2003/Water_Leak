import { Component, OnInit, AfterViewInit, inject, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import Chart from 'chart.js/auto';
import { ManualMeterService } from '../services/manual-meter.service';
import { ManualModel } from '../models/manual-model.interface';
import ChartDataLabels from 'chartjs-plugin-datalabels';
Chart.register(ChartDataLabels);
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PopupConfirmComponent, PopupMode } from 'my-lib';

@Component({
  selector: 'app-manual-model',
  standalone: true,
  templateUrl: './manual-model.component.html',
  styleUrls: ['./manual-model.component.scss'],
  imports: [CommonModule, FormsModule, PopupConfirmComponent]
})
export class ManualModelComponent implements OnInit, AfterViewInit {
  chart: Chart | null = null;
  meters: ManualModel[] = [];
  selectedMeterId: string = '';
  selectedDate: string = '';

  showThresholdModal: boolean = false;
  thresholdMethod: 'manual' | 'yesterday' = 'manual';
  manualThresholdValue: number | null = null;
  yesterdayThreshold: number | null = null;

  showPopup: boolean = false;
  popupTitle: string = '';
  popupMessage: string = '';
  popupMode: PopupMode = PopupMode.SUCCESS;
  PopupMode = PopupMode;

  private route = inject(ActivatedRoute);
  private manualMeterService = inject(ManualMeterService);
  private cdr = inject(ChangeDetectorRef);

  get selectedMeter(): ManualModel | undefined {
    return this.meters.find(m => m._id === this.selectedMeterId);
  }

  get thresholdValue(): number {
    const meter = this.selectedMeter;
    return meter && meter.threshold ? meter.threshold.threshold_value : 0;
  }
  ngOnInit(): void {
  const today = new Date();
  this.selectedDate = today.toISOString().slice(0, 10);
  this.route.paramMap.subscribe(params => {
    const meterIdFromRoute = params.get('meterId');

    this.manualMeterService.getManualMeters(true).subscribe(meters => {
      this.meters = Array.isArray(meters) ? meters : [];

      if (meterIdFromRoute && this.meters.some(m => m._id === meterIdFromRoute)) {
        this.selectedMeterId = meterIdFromRoute;
      } 
      else if (!this.selectedMeterId || !this.meters.some(m => m._id === this.selectedMeterId)) {
        this.selectedMeterId = this.meters[0]?._id ?? '';
      }

      this.cdr.detectChanges();

      setTimeout(() => {
        const select = document.querySelector('select') as HTMLSelectElement;
        if (select && this.selectedMeterId) {
          select.value = this.selectedMeterId;
        }

        if (this.selectedMeterId) {
          this.drawChart(this.selectedMeterId);
        }
      }, 150);
    });
  });
}



  ngAfterViewInit(): void {
    if (this.selectedMeterId) {
      setTimeout(() => this.drawChart(this.selectedMeterId), 300);
    }
  }

  onMeterChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    this.selectedMeterId = select.value;
    this.drawChart(this.selectedMeterId);
  }

  onDateChange(event: Event) {
    const input = event.target as HTMLInputElement;
    this.selectedDate = input.value;
    setTimeout(() => this.drawChart(this.selectedMeterId), 0);
  }

  async drawChart(meterId: string) {
    const startDate = this.selectedDate ? new Date(this.selectedDate) : new Date();
    const labels: string[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(startDate);
      d.setDate(startDate.getDate() + i);
      const day = d.getDate().toString().padStart(2, '0');
      const month = (d.getMonth() + 1).toString().padStart(2, '0');
      const year = d.getFullYear();
      labels.push(`${day}/${month}/${year}`);
    }

    const meter = this.meters.find(m => m._id === meterId);
    let flowData: number[] = [];

    if (meter && meter.measurement) {
      const measurements = Array.isArray(meter.measurement) ? meter.measurement : [meter.measurement];
      flowData = labels.map(label => {
        const found = measurements.find(measurement => {
          const time = measurement?.measurement_time ? new Date(measurement.measurement_time) : null;
          if (!time) return false;
          const day = time.getDate().toString().padStart(2, '0');
          const month = (time.getMonth() + 1).toString().padStart(2, '0');
          const year = time.getFullYear();
          return label === `${day}/${month}/${year}`;
        });
        return found ? found.instant_flow ?? 0 : 0;
      });
    } else {
      flowData = Array(7).fill(0);
    }

    const thresholdData = Array(7).fill(this.thresholdValue);
    const thresholdPointColors = flowData.map(v => v === 0 ? '#cccccc' : '#b23838ff');

    const datasets = [
      {
        label: 'Ngưỡng',
        data: thresholdData,
        borderColor: '#38b26dff',
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: thresholdPointColors,
        fill: false,
        tension: 0,
        borderDash: [8, 4],
        datalabels: {
          display: (ctx: any) => ctx.dataIndex === 0,
          color: '#38b26dff',
          font: { weight: 'bold' as const, size: 15 },
          anchor: 'end' as const,
          align: 'right' as const,
          offset: 16,
          formatter: (value: number, ctx: any) => ctx.dataIndex === 0 ? `${value.toFixed(3)}` : ''
        }
      },
      {
        label: 'Dữ liệu đo',
        data: flowData,
        borderColor: '#ff7300ff',
        backgroundColor: 'rgba(245,101,101,0.1)',
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: '#eec81cff',
        fill: false,
        tension: 0.2
      },
    ];

    const canvas = document.getElementById('meterChart') as HTMLCanvasElement;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (this.chart) {
      this.chart.destroy();
    }

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          title: {
            display: true,
            text: 'Biểu đồ lưu lượng so với ngưỡng',
            font: { size: 18 }
          },
          datalabels: { display: true }
        },
        scales: {
          x: { title: { display: true, text: 'Ngày hiển thị', font: { size: 15 } } },
          y: { title: { display: true, text: 'Lưu lượng', font: { size: 15 } } }
        }
      },
    });
  }

  getTodayText(): string {
    const today = new Date();
    return today.toLocaleDateString('vi-VN', {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
  }

  openThresholdModal(): void {
    if (!this.selectedMeterId) return;
    this.showThresholdModal = true;
    this.thresholdMethod = 'manual';
    this.manualThresholdValue = null;
    this.loadYesterdayThreshold();
  }

  closeThresholdModal(): void {
    this.showThresholdModal = false;
    this.thresholdMethod = 'manual';
    this.manualThresholdValue = null;
    this.yesterdayThreshold = null;
  }

  onMethodChange(): void {
    if (this.thresholdMethod === 'manual') {
      this.manualThresholdValue = null;
    }
  }

  getYesterdayText(): string {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday.toLocaleDateString('vi-VN', {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
  }

  getConfirmButtonText(): string {
    return this.thresholdMethod === 'manual' ? 'Đặt ngưỡng' : 'Sử dụng ngưỡng hôm qua';
  }

  loadYesterdayThreshold(): void {
    if (!this.selectedMeterId) return;

    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayString = yesterday.toISOString().split('T')[0];

    this.manualMeterService.getThresholdByDate(this.selectedMeterId, yesterdayString)
      .subscribe({
        next: (threshold) => this.yesterdayThreshold = threshold,
        error: (err) => {
          console.error('Error loading yesterday threshold:', err);
          this.yesterdayThreshold = null;
        }
      });
  }

  isValidThreshold(): boolean {
    if (!this.selectedMeterId) return false;
    if (this.thresholdMethod === 'manual') {
      return this.manualThresholdValue !== null && this.manualThresholdValue >= 0 && !isNaN(this.manualThresholdValue);
    } else {
      return this.yesterdayThreshold !== null;
    }
  }

  setThreshold(): void {
    if (!this.selectedMeterId || !this.isValidThreshold()) return;

    let thresholdValue: number;
    let successMessage: string;

    if (this.thresholdMethod === 'manual') {
      thresholdValue = this.manualThresholdValue!;
      successMessage = `Đã đặt ngưỡng ${thresholdValue} thành công!`;
    } else {
      thresholdValue = this.yesterdayThreshold!;
      successMessage = `Đã sử dụng ngưỡng hôm qua (${thresholdValue}) thành công!`;
    }

    this.manualMeterService.setThreshold(this.selectedMeterId, thresholdValue)
      .subscribe({
        next: () => {
          this.showSuccessPopup(successMessage);
          this.closeThresholdModal();

          // Reload meters nhưng giữ selectedMeterId nếu còn tồn tại
          const currentId = this.selectedMeterId;
          this.manualMeterService.getManualMeters(true).subscribe(meters => {
            this.meters = Array.isArray(meters) ? meters : [];
            if (currentId && this.meters.some(m => m._id === currentId)) {
              this.selectedMeterId = currentId;
            } else {
              this.selectedMeterId = this.meters[0]?._id ?? '';
            }

            // cập nhật view và vẽ lại chart
            try { this.cdr.detectChanges(); } catch (e) {}
            setTimeout(() => {
              if (this.selectedMeterId) this.drawChart(this.selectedMeterId);
            }, 120);
          });
        },
        error: (err) => {
          console.error('Error setting threshold:', err);
          this.showErrorPopup('Có lỗi xảy ra khi đặt ngưỡng. Vui lòng thử lại!');
        }
      });
  }

  showSuccessPopup(message: string): void {
    this.popupTitle = 'Thành công';
    this.popupMessage = message;
    this.popupMode = PopupMode.SUCCESS;
    this.showPopup = true;
  }

  showErrorPopup(message: string): void {
    this.popupTitle = 'Lỗi';
    this.popupMessage = message;
    this.popupMode = PopupMode.ERROR;
    this.showPopup = true;
  }

  onPopupConfirm(): void {
    this.showPopup = false;
  }

  onPopupCancel(): void {
    this.showPopup = false;
  }
}
