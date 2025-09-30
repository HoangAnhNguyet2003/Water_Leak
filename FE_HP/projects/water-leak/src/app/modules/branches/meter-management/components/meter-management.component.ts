import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router,ActivatedRoute  } from '@angular/router';
import { trigger, transition, style, animate } from '@angular/animations';
import { WaterMeter, WaterMeterFilter } from '../models/water-meter.interface';
import { WaterMeterService } from '../services/water-meter.service';
import { PredictiveModel } from '../../predictive-model/models';

@Component({
  selector: 'app-water-meter-info',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './meter-management.component.html',
  styleUrls: ['./meter-management.component.scss'],
  animations: [
    trigger('slideInOut', [
      transition(':enter', [
        style({ height: '0', opacity: 0, overflow: 'hidden' }),
        animate('300ms ease-in-out', style({ height: '*', opacity: 1 }))
      ]),
      transition(':leave', [
        style({ height: '*', opacity: 1, overflow: 'hidden' }),
        animate('300ms ease-in-out', style({ height: '0', opacity: 0 }))
      ])
    ])
  ]
})
export class MeterManagementComponent implements OnInit {
  getRepairInfo(meter: WaterMeter): string {
    if (!meter.repair) return 'Không có thông tin sửa chữa';
    const r = meter.repair;
    let info = `Thời gian sửa: ${this.formatDate(r.repair_time)}`;
    if (r.leak_reason) info += ` | Lý do: ${r.leak_reason}`;
    return info;
  }

    getPredictionClass(meter: WaterMeter): string {
      return 'prediction-green';
    }
  waterMeters = signal<WaterMeter[]>([]);
  filteredMeters = signal<WaterMeter[]>([]);
  filter = signal<WaterMeterFilter & {
    thresholdOperator?: '>' | '<' | '=';
    thresholdValue?: number;
    sortOrder?: 'asc' | 'desc';
  }>({
    searchTerm: '',
    statusFilter: '',
    thresholdOperator: '>',
    thresholdValue: undefined,
    sortOrder: 'desc'
  });

  constructor(private router: Router, private waterMeterService: WaterMeterService,private route: ActivatedRoute) {}

  ngOnInit(): void {
    const meterId = this.route.snapshot.paramMap.get('meterId');
    this.waterMeterService.getMyMeters(true).subscribe(meters => {
      this.waterMeters.set(meters);
      this.filteredMeters.set(meters);
    });
  }

  private isValidWaterMeter(meter: any): meter is WaterMeter {
    return meter && typeof meter._id === 'string' && typeof meter.meter_name === 'string';
  }

  onSearch(): void {
    const currentFilter = this.filter();
    const meters = this.waterMeters();
    if (!meters || !Array.isArray(meters)) return;
    let filtered = meters.filter(meter => {
      if (!this.isValidWaterMeter(meter)) return false;
      const matchesSearch = !currentFilter.searchTerm ||
        meter.meter_name.toLowerCase().includes(currentFilter.searchTerm.toLowerCase());
      const matchesStatus = !currentFilter.statusFilter || 'Normal' === currentFilter.statusFilter;
      // Lọc vượt ngưỡng
      let matchesThreshold = true;
      if (
        currentFilter.thresholdOperator &&
        typeof currentFilter.thresholdValue === 'number' &&
        !isNaN(currentFilter.thresholdValue)
      ) {
        const { percent } = this.getThresholdInfo(meter);
        switch (currentFilter.thresholdOperator) {
          case '>': matchesThreshold = percent > currentFilter.thresholdValue; break;
          case '<': matchesThreshold = percent < currentFilter.thresholdValue; break;
          case '=': matchesThreshold = Math.abs(percent - currentFilter.thresholdValue) < 0.01; break;
        }
      }
      return matchesSearch && matchesStatus && matchesThreshold;
    });

    if (currentFilter.sortOrder) {
      filtered.sort((a, b) => {
        const percentA = this.getThresholdInfo(a).percent;
        const percentB = this.getThresholdInfo(b).percent;
        if (currentFilter.sortOrder === 'asc') {
          return percentA - percentB;
        } else {
          return percentB - percentA;
        }
      });
    }

    this.filteredMeters.set(filtered);
  }

  onFilterChange(): void {
    this.onSearch();
  }

  private searchTimeout: any;
  onSearchTermChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const value = target?.value ?? '';
    this.filter.update(curr => ({ ...curr, searchTerm: value }));
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }
    this.searchTimeout = setTimeout(() => this.onSearch(), 250);
  }

  trackByMeterId(index: number, meter: WaterMeter): string {
    return meter._id;
  }

  toggleDetails(meterId: string): void {
    const meters = this.filteredMeters();
    const updatedMeters = meters.map(meter =>
      meter._id === meterId ? { ...meter, expanded: !meter.expanded } : meter
    );
    this.filteredMeters.set(updatedMeters);
    const allMeters = this.waterMeters();
    const updatedAllMeters = allMeters.map(meter =>
      meter._id === meterId ? { ...meter, expanded: !meter.expanded } : meter
    );
    this.waterMeters.set(updatedAllMeters);
  }

  viewDetails(meterId: string): void {
    this.toggleDetails(meterId);
  }

  isExpanded(meterId: string): boolean {
    const meter = this.filteredMeters().find(m => m._id === meterId);
    return meter?.expanded || false;
  }

  viewChart(meterId: string): void {
  this.router.navigate(['/branches', 'manual-model', meterId]);
}


  formatDate(val: string | Date | null): string {
  if (!val) return '';

  let d: Date;

  if (val instanceof Date) {
    d = val;
  }
  else if (typeof val === 'object' && (val as any).$date) {
    d = new Date((val as any).$date);
  }
  else if (typeof val === 'string') {
    d = new Date(val);
  }
  else {
    return '';
  }

  if (isNaN(d.getTime())) return val as string;
  const day = d.getUTCDate().toString().padStart(2, '0');
  const month = (d.getUTCMonth() + 1).toString().padStart(2, '0');
  const year = d.getUTCFullYear();
  return `${day}/${month}/${year}`;
}


  getThresholdInfo(meter: WaterMeter): { percent: number, className: string } {
    let percent = 0;
    if (meter.measurement && meter.threshold) {
      const flow = meter.measurement.instant_flow;
      const threshold = meter.threshold.threshold_value;
      if (typeof flow === 'number' && typeof threshold === 'number' && threshold !== 0) {
        percent = (flow / threshold - 1) * 100;
      }
    }
    return {
      percent: percent > 0 ? percent : 0,
      className: percent > 30 ? 'threshold-red' : 'threshold-green'
    };
  }


   getMeterConclusionToday(meter: WaterMeter): { text: string; color: string } {
  if (!meter || !meter.prediction) {
    return { text: 'Chưa có dữ liệu', color: '' };
  }

  const now = new Date();
  const todayStr = `${now.getUTCDate().toString().padStart(2,'0')}/${(now.getUTCMonth()+1).toString().padStart(2,'0')}/${now.getFullYear()}`;

  const pred = meter.prediction;
  const predDate = new Date(pred.prediction_time);
  const predStr = `${predDate.getUTCDate().toString().padStart(2,'0')}/${(predDate.getUTCMonth()+1).toString().padStart(2,'0')}/${predDate.getFullYear()}`;

  if (predStr !== todayStr) {
    return { text: 'Chưa có dữ liệu', color: '' };
  }
  const score = pred.predicted_label === 'leak' ? 33 : 0;
  const text = score > 50 ? 'Nghi ngờ cao' : 'Nghi ngờ thấp';
  const colorClass = text === 'Nghi ngờ cao' ? 'prediction-red' : 'prediction-green';

  return { text, color: colorClass };
}

}
