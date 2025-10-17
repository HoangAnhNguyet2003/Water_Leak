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
    const statusFilter = this.route.snapshot.queryParamMap.get('statusFilter');

    this.waterMeterService.getMyMeters(true).subscribe(meters => {
      this.waterMeters.set(meters);
      this.filteredMeters.set(meters);

      if (statusFilter) {
        this.filter.update(curr => ({ ...curr, statusFilter }));
        this.onSearch();
      }
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

  const matchesSearch =
    !currentFilter.searchTerm ||
    meter.meter_name.toLowerCase().includes(currentFilter.searchTerm.toLowerCase());

  const matchesStatus =
    !currentFilter.statusFilter ||
    meter.predictions?.some(pred =>
      pred.predicted_label === currentFilter.statusFilter ||
      pred.confidence === currentFilter.statusFilter
    );

  // Lọc vượt ngưỡng
  let matchesThreshold = true;
  if (
    currentFilter.thresholdOperator &&
    typeof currentFilter.thresholdValue === 'number' &&
    !isNaN(currentFilter.thresholdValue)
  ) {
    const { percent } = this.getThresholdInfo(meter);
    switch (currentFilter.thresholdOperator) {
      case '>':
        matchesThreshold = percent > currentFilter.thresholdValue;
        break;
      case '<':
        matchesThreshold = percent < currentFilter.thresholdValue;
        break;
      case '=':
        matchesThreshold = Math.abs(percent - currentFilter.thresholdValue) < 0.01;
        break;
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

  formatDate(val: string | Date | { $date: string } | null): string {
  if (!val) return '';

  let d: Date;

  if (val instanceof Date) {
    d = val;
  } else if (typeof val === 'object' && '$date' in val) {
    d = new Date((val as any).$date);
  } else if (typeof val === 'string') {
    d = new Date(val);
  } else {
    return '';
  }

  if (isNaN(d.getTime())) return '';

  const day = d.getDate().toString().padStart(2, '0');
  const month = (d.getMonth() + 1).toString().padStart(2, '0');
  const year = d.getFullYear();

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
  // c tính kết luận từ đây
  public getMeterConclusionToday(meter: WaterMeter): { text: string; color: string } {
  if (!meter) return { text: 'Chưa có dữ liệu', color: '' };

  const today = new Date();
  const todayStr = `${today.getDate().toString().padStart(2,'0')}/${(today.getMonth()+1).toString().padStart(2,'0')}/${today.getFullYear()}`;

  const lstmPredictions = meter.predictions?.filter(p =>
    p.model_name?.toUpperCase().includes('LSTM') && !p.model_name?.toUpperCase().includes('AUTO')
  ) ?? [];

  const lstmAutoencoder = meter.predictions?.filter(p =>
    p.model_name?.toUpperCase().includes('AUTO')
  ) ?? [];
  const formatDate = (pred: any): string => {
    const dateRaw = pred?.prediction_time?.$date ?? pred?.prediction_time;
    const d = new Date(dateRaw);
    if (isNaN(d.getTime())) return '';
    return `${d.getDate().toString().padStart(2,'0')}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getFullYear()}`;
  };

  const lstmToday = lstmPredictions.find(p => formatDate(p) === todayStr) ?? null;
  const autoencoderToday = lstmAutoencoder.filter(p => formatDate(p) === todayStr);

  const selectBestPredictionForDay = (preds: any[]): any | null => {
    if (!preds || preds.length === 0) return null;
    if (preds.length === 1) return preds[0];
    const leaks = preds.filter(p => ['LEAK','NNTHAP','NNTB','NNCAO'].includes((p.predicted_label ?? '').toString().trim().toUpperCase()));
    const candidates = leaks.length > 0 ? leaks : preds.slice();
    const rank: Record<string, number> = { NNCAO: 3, NNTB: 2, NNTHAP: 1 };
    candidates.sort((a,b) => {
      const aLabel = (a.predicted_label ?? '').toString().trim().toUpperCase();
      const bLabel = (b.predicted_label ?? '').toString().trim().toUpperCase();
      const aConf = (a.confidence ?? '').toString().trim().toUpperCase();
      const bConf = (b.confidence ?? '').toString().trim().toUpperCase();
      const scoreA = rank[aLabel] ?? rank[aConf] ?? 0;
      const scoreB = rank[bLabel] ?? rank[bConf] ?? 0;
      return scoreB - scoreA;
    });
    return candidates[0];
  };

  const autoencoderBest = selectBestPredictionForDay(autoencoderToday);

  if (!lstmToday && !autoencoderBest) return { text: 'Chưa có dữ liệu', color: '' };

  const getScore = (pred: any): number => {
    if (!pred) return 0;
    const label = (pred.predicted_label ?? '').toString().trim().toUpperCase();
    const conf = (pred.confidence ?? '').toString().trim().toUpperCase();
    if (label === 'NORMAL') return 0;
    if (['NNTHAP','NNTB','NNCAO'].includes(label)) return label === 'NNCAO' ? 3 : label === 'NNTB' ? 2 : 1;
    if (label === 'LEAK') {
      if (['NNTHAP','NNTB','NNCAO'].includes(conf)) return conf === 'NNCAO' ? 3 : conf === 'NNTB' ? 2 : 1;
      const num = Number(conf);
      if (!isNaN(num)) return num >= 75 ? 3 : num >= 40 ? 2 : 1;
      return 1;
    }
    return 0;
  };

  const predictions = [lstmToday, autoencoderBest].filter(Boolean);
  const avgScore = predictions.map(getScore).reduce((s,v) => s+v,0)/predictions.length;
  const finalScore = Math.floor(avgScore);

  let text = 'Bình thường';
  let color = 'prediction-green';
  switch(finalScore){
    case 1: text='Rò rỉ nghi ngờ thấp'; color='prediction-green'; break;
    case 2: text='Rò rỉ nghi ngờ trung bình'; color='prediction-yellow'; break;
    case 3: text='Rò rỉ nghi ngờ cao'; color='prediction-red'; break;
  }

  return { text, color };
}

}
