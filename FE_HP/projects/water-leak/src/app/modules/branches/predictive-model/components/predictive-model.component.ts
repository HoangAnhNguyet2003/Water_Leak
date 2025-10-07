import { Component, OnInit } from '@angular/core';
import { PredictiveModelService } from '../services/predictive-model.service';
import { ManualMeterService } from '../../manual-model/services/manual-meter.service';
import { ManualModel } from '../../manual-model/models/manual-model.interface';
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
  showLeakPopup: boolean = false;
  leakingMeters: ManualModel[] = [];
  filteredLeakingMeters: ManualModel[] = [];
  sortOrder: 'asc' | 'desc' = 'desc';

  constructor(private predictiveService: PredictiveModelService, private manualMeterService: ManualMeterService) {}

  ngOnInit(): void {
    this.loadData();
    this.loadLeakingMeters();
  }

    private loadData(force = true): void {
    this.predictiveService.getManualMeters(force).subscribe(items => {
      // Filter duplicate meters by meter_name, keep the first occurrence
      const uniqueItems = items.filter((meter, index, arr) =>
        arr.findIndex(m => m.meter_name === meter.meter_name) === index
      );

      this.data = uniqueItems;

      if (uniqueItems.length > 0) {
        this.selectedMeter = uniqueItems[0];
        // Bắt đầu từ ngày có dữ liệu (04/10/2025)
        this.generateDates(new Date('2025-10-04'));
        this.buildTableWithSeparateAPIs(this.selectedMeter);
      }
    });
  }

  private loadLeakingMeters(): void {
    this.manualMeterService.getManualMeters(true).subscribe(meters => {
      this.leakingMeters = meters.filter(meter => {
        return meter.measurement && meter.threshold && meter.measurement.instant_flow > meter.threshold.threshold_value;
      });
      const leakPopupShown = sessionStorage.getItem('leakPopupShown');
      this.showLeakPopup = this.leakingMeters.length > 0 && !leakPopupShown;
      if (this.showLeakPopup) {
        sessionStorage.setItem('leakPopupShown', 'true');
      }
      this.filterLeakingMeters();
    });
  }

  onMeterChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.selectedMeter = this.data.find(m => m._id === value) ?? null;
    if (this.selectedMeter) {
      this.buildTableWithSeparateAPIs(this.selectedMeter);
    }
  }

  onDateChange(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    if (value) {
      const selectedDate = new Date(value);
      this.generateDates(selectedDate);
      if (this.selectedMeter) this.buildTableWithSeparateAPIs(this.selectedMeter);
    }
  }

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



  getConclusionByDate(dateStr: string): { text: string, color: string } {
    if (!this.tableData.models || this.tableData.models.length < 2) {
      return { text: 'Chưa có dữ liệu', color: this.getColor('Chưa có dữ liệu') };
    }

    const idx = this.dates.indexOf(dateStr);
    if (idx === -1) return { text: 'Chưa có dữ liệu', color: this.getColor('Chưa có dữ liệu') };

    const lstmResult = this.tableData.models.find(m => m.name === 'LSTM')?.results[idx] || 'Chưa có dữ liệu';
    const autoencoderResult = this.tableData.models.find(m => m.name === 'LSTM_AUTOENCODER')?.results[idx] || 'Chưa có dữ liệu';

    const lstmLabel = lstmResult.split(' (')[0];
    const autoencoderLabel = autoencoderResult.split(' (')[0];

    // Logic kết hợp theo thứ tự ưu tiên: Rò rỉ > Nghi ngờ cao > Nghi ngờ trung bình > Nghi ngờ thấp > Bình thường
    const priorityOrder = [
      'Rò rỉ nghi ngờ cao', 'Rò rỉ nghi ngờ trung bình', 'Rò rỉ nghi ngờ thấp', 'Rò rỉ',
      'Nghi ngờ cao', 'Nghi ngờ trung bình', 'Nghi ngờ thấp', 'Bình thường'
    ];

    for (const priority of priorityOrder) {
      if (lstmLabel === priority || autoencoderLabel === priority) {
        return { text: priority, color: this.getColor(priority) };
      }
    }

    return { text: 'Chưa có dữ liệu', color: this.getColor('Chưa có dữ liệu') };
  }

  // Method riêng để tính conclusion với data trực tiếp sử dụng confidence hierarchy
  private getConclusionByDateDirect(dateStr: string, lstmAutoencoder: any[], lstmPredictions: any[]): string {
    // Tìm prediction cho LSTM
    const lstmPred = lstmPredictions.find(pred => {
      const dateString = pred.prediction_time?.$date || pred.prediction_time;
      const predDate = new Date(dateString);
      const day = predDate.getUTCDate().toString().padStart(2, '0');
      const month = (predDate.getUTCMonth() + 1).toString().padStart(2, '0');
      const year = predDate.getUTCFullYear();
      const predictionDate = `${day}/${month}/${year}`;
      return predictionDate === dateStr;
    });

    // Tìm prediction cho LSTM Autoencoder
    const autoencoderPred = lstmAutoencoder.find(pred => {
      const dateString = pred.prediction_time?.$date || pred.prediction_time;
      const predDate = new Date(dateString);
      const day = predDate.getUTCDate().toString().padStart(2, '0');
      const month = (predDate.getUTCMonth() + 1).toString().padStart(2, '0');
      const year = predDate.getUTCFullYear();
      const predictionDate = `${day}/${month}/${year}`;
      return predictionDate === dateStr;
    });

    const confidenceOrder = ['NNcao', 'NNTB', 'NNthap'];
    let highestConfidence: string | null = null;
    let conclusion = 'Chưa có dữ liệu';

    [lstmPred, autoencoderPred].forEach(pred => {
      if (pred && pred.confidence && confidenceOrder.includes(pred.confidence)) {
        const confidenceRank = confidenceOrder.indexOf(pred.confidence);
        const currentRank = highestConfidence ? confidenceOrder.indexOf(highestConfidence) : -1;

        if (currentRank === -1 || confidenceRank < currentRank) {
          highestConfidence = pred.confidence;
          if (pred.confidence === 'NNcao') {
            conclusion = pred.predicted_label === 'leak' ? 'Rò rỉ nghi ngờ cao' : 'Nghi ngờ cao';
          } else if (pred.confidence === 'NNTB') {
            conclusion = pred.predicted_label === 'leak' ? 'Rò rỉ nghi ngờ trung bình' : 'Nghi ngờ trung bình';
          } else if (pred.confidence === 'NNthap') {
            conclusion = pred.predicted_label === 'leak' ? 'Rò rỉ nghi ngờ thấp' : 'Bình thường';
          }
        }
      }
    });

    if (conclusion === 'Chưa có dữ liệu') {
      const lstmLabel = lstmPred ? (
        lstmPred.predicted_label === 'leak' ? 'Rò rỉ' :
        lstmPred.predicted_label === 'normal' ? 'Bình thường' : null
      ) : null;

      const autoencoderLabel = autoencoderPred ? (
        autoencoderPred.predicted_label === 'leak' ? 'Rò rỉ' :
        autoencoderPred.predicted_label === 'normal' ? 'Bình thường' : null
      ) : null;

      if (lstmLabel === 'Rò rỉ' || autoencoderLabel === 'Rò rỉ') {
        conclusion = 'Rò rỉ';
      } else if (lstmLabel === 'Bình thường' || autoencoderLabel === 'Bình thường') {
        conclusion = 'Bình thường';
      }
    }

    return conclusion;
  }

  getColor(text: string): string {
    // Extract the label part before parentheses for color determination
    const label = text.split(' (')[0];
    switch (label) {
      case 'Rò rỉ nghi ngờ cao':
      case 'Rò rỉ':
      case 'Nghi ngờ cao': return '#c62828';        // Đỏ đậm
      case 'Rò rỉ nghi ngờ trung bình':
      case 'Nghi ngờ trung bình': return '#f57c00'; // Cam
      case 'Rò rỉ nghi ngờ thấp':
      case 'Nghi ngờ thấp': return '#fbc02d';       // Vàng
      case 'Bình thường': return '#2e7d32';         // Xanh
      case 'Không xác định': return '#9e9e9e';      // Xám đậm
      default: return '#616161';                    // Xám
    }
  }

  getPredictionClass(text: string): string {
    // Extract the label part before parentheses for class determination
    const label = text.split(' (')[0];
    switch (label) {
      case 'Rò rỉ nghi ngờ cao':
      case 'Rò rỉ':
      case 'Nghi ngờ cao': return 'prediction-high';
      case 'Rò rỉ nghi ngờ trung bình':
      case 'Nghi ngờ trung bình': return 'prediction-medium';
      case 'Rò rỉ nghi ngờ thấp':
      case 'Nghi ngờ thấp': return 'prediction-low';
      case 'Bình thường': return 'prediction-normal';
      case 'Không xác định': return 'prediction-undefined';
      default: return 'prediction-unknown';
    }
  }

  getTotalModelsCount(): number {
    // Luôn trả về 2 vì chỉ có LSTM và LSTM_AUTOENCODER
    return 2;
  }

  // Reload khi quay lại trang
  reload(): void {
    this.loadData(true);
  }

  getExceedancePercentage(meter: ManualModel): number {
    if (!meter.measurement || !meter.threshold) return 0;
    const exceed = meter.measurement.instant_flow - meter.threshold.threshold_value;
    return Math.round((exceed / meter.threshold.threshold_value) * 100);
  }

  filterLeakingMeters() {
    this.filteredLeakingMeters = this.leakingMeters.filter(m => this.getExceedancePercentage(m) >= 0); // all
    this.sortLeakingMeters();
  }

  sortLeakingMeters() {
    this.filteredLeakingMeters.sort((a, b) => {
      const aExceed = this.getExceedancePercentage(a);
      const bExceed = this.getExceedancePercentage(b);
      if (this.sortOrder === 'asc') {
        return aExceed - bExceed;
      } else {
        return bExceed - aExceed;
      }
    });
  }

  closeLeakPopup() {
    this.showLeakPopup = false;
  }

  // Method mới sử dụng 2 API riêng biệt
  private buildTableWithSeparateAPIs(meter: PredictiveModel): void {
    Promise.all([
      this.predictiveService.getLSTMAutoencoderPredictions(meter._id).toPromise(),
      this.predictiveService.getLSTMPredictions(meter._id).toPromise()
    ]).then(([lstmAutoencoder, lstmPredictions]) => {
      this.buildCombinedTable(meter, lstmAutoencoder || [], lstmPredictions || []);
    }).catch(error => {
      console.error('Error loading predictions:', error);
      // Fallback: hiển thị bảng trống với cả 3 dòng
      this.tableData = {
        models: [
          { name: 'LSTM', results: this.dates.map(() => 'Chưa có dữ liệu') },
          { name: 'LSTM_AUTOENCODER', results: this.dates.map(() => 'Chưa có dữ liệu') },
          { name: 'Kết luận', results: this.dates.map(() => 'Chưa có dữ liệu') }
        ]
      };
    });
  }


  private selectBestPredictionForDay(predictions: any[]): any {
    if (predictions.length === 1) {
      return predictions[0];
    }

    // 1. Tách predictions theo label
    const leakPredictions = predictions.filter(p => p.predicted_label === 'leak');
    const normalPredictions = predictions.filter(p => p.predicted_label === 'normal');

    // 2. Ưu tiên leak predictions
    let candidatePredictions = leakPredictions.length > 0 ? leakPredictions : normalPredictions;

    // 3. Sắp xếp theo confidence hierarchy: NNcao > NNTB > NNthap
    const confidenceRank: { [key: string]: number } = { 'NNcao': 3, 'NNTB': 2, 'NNthap': 1 };

    candidatePredictions.sort((a, b) => {
      const aRank = confidenceRank[a.confidence as string] || 0;
      const bRank = confidenceRank[b.confidence as string] || 0;
      return bRank - aRank; // Sắp xếp giảm dần (cao nhất trước)
    });

    return candidatePredictions[0];
  }

  private buildCombinedTable(meter: PredictiveModel, lstmAutoencoder: any[], lstmPredictions: any[]): void {

    const models = [];


    models.push({
      name: 'LSTM',
      results: this.dates.map(dateStr => {
        const predForDate = lstmPredictions.find(pred => {
          // Parse MongoDB date format {$date: 'ISO_STRING'}
          const dateString = pred.prediction_time?.$date || pred.prediction_time;
          const predDate = new Date(dateString);

          const day = predDate.getUTCDate().toString().padStart(2, '0');
          const month = (predDate.getUTCMonth() + 1).toString().padStart(2, '0');
          const year = predDate.getUTCFullYear();
          const predictionDate = `${day}/${month}/${year}`;
          return predictionDate === dateStr;
        });

        if (predForDate) {
          const label = predForDate.predicted_label === 'leak' ? 'Rò rỉ' :
                       predForDate.predicted_label === 'normal' ? 'Bình thường' :
                       predForDate.predicted_label || 'Không xác định';
          let confidence = 'N/A';

          if (predForDate.confidence && predForDate.confidence !== 'nan') {
            // Xử lý confidence Vietnamese hoặc số
            if (['NNcao', 'NNTB', 'NNthap'].includes(predForDate.confidence)) {
              confidence = predForDate.confidence; // Giữ nguyên Vietnamese confidence
            } else if (!isNaN(Number(predForDate.confidence))) {
              confidence = `${predForDate.confidence}%`; // Thêm % cho confidence số
            } else {
              confidence = predForDate.confidence; // Hiển thị as-is cho các format khác
            }
          }

          return `${label} (${confidence})`;
        }
        return 'Chưa có dữ liệu';
      })
    });

    models.push({
      name: 'LSTM_AUTOENCODER',
      results: this.dates.map(dateStr => {
        const predictionsForDate = lstmAutoencoder.filter(pred => {
          const dateString = pred.prediction_time?.$date || pred.prediction_time;
          const predDate = new Date(dateString);

          const day = predDate.getUTCDate().toString().padStart(2, '0');
          const month = (predDate.getUTCMonth() + 1).toString().padStart(2, '0');
          const year = predDate.getUTCFullYear();
          const predictionDate = `${day}/${month}/${year}`;
          return predictionDate === dateStr;
        });

        if (predictionsForDate.length > 0) {
          const bestPrediction = this.selectBestPredictionForDay(predictionsForDate);

          const label = bestPrediction.predicted_label === 'leak' ? 'Rò rỉ' :
                       bestPrediction.predicted_label === 'normal' ? 'Bình thường' :
                       bestPrediction.predicted_label || 'Không xác định';
          let confidence = 'N/A';

          if (bestPrediction.confidence && bestPrediction.confidence !== 'nan') {
            if (['NNcao', 'NNTB', 'NNthap'].includes(bestPrediction.confidence)) {
              confidence = bestPrediction.confidence;
            } else if (!isNaN(Number(bestPrediction.confidence))) {
              confidence = `${bestPrediction.confidence}%`;
            } else {
              confidence = bestPrediction.confidence;
            }
          }

          return `${label} (${confidence})`;
        }
        return 'Chưa có dữ liệu';
      })
    });    // 3. Dòng kết luận dựa trên quy tắc confidence
    models.push({
      name: 'Kết luận',
      results: this.dates.map(dateStr => {
        return this.getConclusionByDateDirect(dateStr, lstmAutoencoder, lstmPredictions);
      })
    });

    this.tableData = { models };
  }

  private getPredictionResultForDate(predictions: any[], targetDate: string): string {
    for (const pred of predictions) {
      const predDate = new Date(pred.prediction_time);
      const day = predDate.getUTCDate().toString().padStart(2, '0');
      const month = (predDate.getUTCMonth() + 1).toString().padStart(2, '0');
      const year = predDate.getUTCFullYear();
      const predictionDate = `${day}/${month}/${year}`;

      if (predictionDate === targetDate) {
        return pred.predicted_label === 'normal' ? 'Nghi ngờ thấp' : 'Nghi ngờ cao';
      }
    }
    return 'Chưa có dữ liệu';
  }
}
