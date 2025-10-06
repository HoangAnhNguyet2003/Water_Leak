import { Component, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { PredictiveModelService } from '../services/predictive-model.service';
import { PredictiveModel } from '../models';

@Component({
  selector: 'app-predictive-model',
  templateUrl: './predictive-model.component.html',
  styleUrls: ['./predictive-model.component.scss']
})
export class PredictiveModelComponent implements OnInit {
  data: PredictiveModel[] = [];
  selectedMeter: PredictiveModel | null = null;
  dates: string[] = [];
  tableData: { models: { name: string; results: string[] }[] } = { models: [] };

  private router = inject(Router);
  constructor(private predictiveService: PredictiveModelService) {}

  ngOnInit(): void {
    this.loadData();
  }

  private loadData(force = false): void {
    this.predictiveService.getManualMeters(force).subscribe(items => {
      this.data = items;
      if (items.length > 0) {
        this.selectedMeter = items[0];
        this.generateDates(new Date()); // tạo ngày hôm nay
        this.buildTable(this.selectedMeter);
      }
    });
  }

  onMeterChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.selectedMeter = this.data.find(m => m._id === value) ?? null;
    if (this.selectedMeter) {
      this.buildTable(this.selectedMeter);
    }
  }

  onDateChange(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    if (value) {
      const selectedDate = new Date(value);
      this.generateDates(selectedDate);
      if (this.selectedMeter) this.buildTable(this.selectedMeter);
    }
  }

  // Tạo mảng 7 ngày liên tiếp theo UTC, giữ nguyên ngày như API
  private generateDates(startDate: Date): void {
    this.dates = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(startDate);
      d.setUTCDate(d.getUTCDate() + i); // tăng ngày theo UTC
      const day = d.getUTCDate().toString().padStart(2, '0');
      const month = (d.getUTCMonth() + 1).toString().padStart(2, '0');
      const year = d.getUTCFullYear();
      this.dates.push(`${day}/${month}/${year}`);
    }
  }

  private buildTable(meter: PredictiveModel) {
    if (!meter || !meter.prediction) {
      this.tableData = {
        models: [
          {
            name: 'Không có mô hình',
            results: this.dates.map(() => 'Chưa có dữ liệu')
          }
        ]
      };
      return;
    }

    const modelName = meter.prediction.model_name ?? 'Không rõ';

    // Lấy ngày UTC của prediction
    const predDate = new Date(meter.prediction.prediction_time);
    const day = predDate.getUTCDate().toString().padStart(2, '0');
    const month = (predDate.getUTCMonth() + 1).toString().padStart(2, '0');
    const year = predDate.getUTCFullYear();
    const predictionDate = `${day}/${month}/${year}`;

    this.tableData = {
      models: [
        {
          name: modelName,
          results: this.dates.map(dateStr => {
            if (predictionDate === dateStr) {
              switch (meter.prediction?.predicted_label) {
                case 'leak': return 'Nghi ngờ cao';
                case 'normal': return 'Nghi ngờ thấp';
                default: return 'Chưa có dữ liệu';
              }
            }
            return 'Chưa có dữ liệu';
          })
        }
      ]
    };
    
  }

  getConclusionByDate(dateStr: string): { text: string, color: string } {
    if (!this.tableData.models || this.tableData.models.length === 0) {
      return { text: 'Chưa có dữ liệu', color: this.getColor('Chưa có dữ liệu') };
    }

    let highCount = 0;
    let noDataCount = 0;
    const totalModels = this.tableData.models.length;

    for (const m of this.tableData.models) {
      const idx = this.dates.indexOf(dateStr);
      if (idx === -1) continue;
      const resultForDate = m.results[idx];
      if (resultForDate === 'Nghi ngờ cao') highCount++;
      else if (resultForDate === 'Chưa có dữ liệu') noDataCount++;
    }

    if (noDataCount === totalModels) return { text: 'Chưa có dữ liệu', color: this.getColor('Chưa có dữ liệu') };

    const score = highCount * 33;
    return score > 50 ? { text: 'Nghi ngờ cao', color: this.getColor('Nghi ngờ cao') } : { text: 'Nghi ngờ thấp', color: this.getColor('Nghi ngờ thấp') };
  }

  getColor(text: string): string {
    switch (text) {
      case 'Nghi ngờ cao': return 'red';
      case 'Nghi ngờ thấp': return 'green';
      default: return 'gray';
    }
  }

  // Reload khi quay lại trang
  reload(): void {
    this.loadData(true);
  }
  
  // ===== Re-added: counting and navigation helpers used by the cards =====
  private countByLevel(level: 'low' | 'medium' | 'high'): number {
    const items = this.data || [];
    const today = new Date();
    const day = today.getUTCDate().toString().padStart(2, '0');
    const month = (today.getUTCMonth() + 1).toString().padStart(2, '0');
    const year = today.getUTCFullYear();
    const todayStr = `${day}/${month}/${year}`;
    return items.reduce((acc, m) => {
      const text = this.getConclusionTodayText(m, todayStr);
      if (level === 'high') return acc + (text === 'Nghi ngờ cao' ? 1 : 0);
      if (level === 'medium') return acc + (text === 'Nghi ngờ trung bình' ? 1 : 0);
      // low: 'Nghi ngờ thấp' or 'Chưa có dữ liệu'
      return acc + (text === 'Nghi ngờ thấp' || text === 'Chưa có dữ liệu' ? 1 : 0);
    }, 0);
  }

  navigateToMeters(level: 'low' | 'medium' | 'high'): void {
    this.router.navigate(['/branches/meter-management'], { queryParams: { suspicion: level } });
  }

  private getConclusionTodayText(m: PredictiveModel, dateStr: string): 'Nghi ngờ cao'|'Nghi ngờ thấp'|'Nghi ngờ trung bình'|'Chưa có dữ liệu' {
    if (!m || !m.prediction) return 'Chưa có dữ liệu';
    const pd = new Date(m.prediction.prediction_time);
    const d = `${pd.getUTCDate().toString().padStart(2,'0')}/${(pd.getUTCMonth()+1).toString().padStart(2,'0')}/${pd.getUTCFullYear()}`;
    if (d !== dateStr) return 'Chưa có dữ liệu';
    if (m.prediction.predicted_label === 'leak') return 'Nghi ngờ cao';
    if (m.prediction.predicted_label === 'normal') return 'Nghi ngờ thấp';
    return 'Nghi ngờ trung bình';
  }

  // Methods for template binding to ensure live recomputation
  totalLow(): number { return this.countByLevel('low'); }
  totalMedium(): number { return this.countByLevel('medium'); }
  totalHigh(): number { return this.countByLevel('high'); }
}
