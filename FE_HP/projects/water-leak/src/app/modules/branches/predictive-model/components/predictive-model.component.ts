import { Component, OnInit } from '@angular/core';
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

  constructor(private predictiveService: PredictiveModelService) {}

  ngOnInit(): void {
    this.loadData();
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
        this.generateDates(new Date());
        this.buildTableWithSeparateAPIs(this.selectedMeter);
      }
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
      d.setUTCDate(d.getUTCDate() + i);
      const day = d.getUTCDate().toString().padStart(2, '0');
      const month = (d.getUTCMonth() + 1).toString().padStart(2, '0');
      const year = d.getUTCFullYear();
      this.dates.push(`${day}/${month}/${year}`);
    }
  }

  private formatDateFromPrediction(pred: any): string {
    const dateString = pred.prediction_time?.$date || pred.prediction_time;
    const predDate = new Date(dateString);
    const day = predDate.getUTCDate().toString().padStart(2, '0');
    const month = (predDate.getUTCMonth() + 1).toString().padStart(2, '0');
    const year = predDate.getUTCFullYear();
    return `${day}/${month}/${year}`;
  }
  private getConclusionByDateDirect(dateStr: string, lstmAutoencoder: any[], lstmPredictions: any[]): string {
    const lstmPred = lstmPredictions.find(pred => this.formatDateFromPrediction(pred) === dateStr);
    const autoencoderPredictions = lstmAutoencoder.filter(pred => this.formatDateFromPrediction(pred) === dateStr);
    const autoencoderPred = autoencoderPredictions.length > 0 ? this.selectBestPredictionForDay(autoencoderPredictions) : null;

    if (!lstmPred && !autoencoderPred) return 'Chưa có dữ liệu';

    const getScore = (pred: any): number => {
      if (!pred) return 0;
      if (pred.predicted_label === 'normal') return 0;
      if (pred.predicted_label === 'leak') {
        if (pred.confidence === 'NNthap') return 1;
        if (pred.confidence === 'NNTB') return 2;
        if (pred.confidence === 'NNcao') return 3;
        return 1;
      }
      return 0;
    };

    const predictions = [lstmPred, autoencoderPred].filter(p => p !== null);
    if (predictions.length === 0) return 'Chưa có dữ liệu';

    const scores = predictions.map(pred => getScore(pred));
    const averageScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;
    const finalScore = Math.floor(averageScore);

    switch (finalScore) {
      case 0: return 'Bình thường';
      case 1: return 'Rò rỉ nghi ngờ thấp';
      case 2: return 'Rò rỉ nghi ngờ trung bình';
      case 3: return 'Rò rỉ nghi ngờ cao';
      default: return 'Bình thường';
    }
  }

  getColor(text: string): string {
    const label = text.split(' (')[0];
    const colorMap: { [key: string]: string } = {
      'Rò rỉ nghi ngờ cao': '#c62828', 'Rò rỉ': '#c62828', 'Nghi ngờ cao': '#c62828',
      'Rò rỉ nghi ngờ trung bình': '#f57c00', 'Nghi ngờ trung bình': '#f57c00',
      'Rò rỉ nghi ngờ thấp': '#fbc02d', 'Nghi ngờ thấp': '#fbc02d',
      'Bình thường': '#2e7d32', 'Không xác định': '#9e9e9e'
    };
    return colorMap[label] || '#616161';
  }

  getPredictionClass(text: string): string {
    const label = text.split(' (')[0];
    const classMap: { [key: string]: string } = {
      'Rò rỉ nghi ngờ cao': 'prediction-high', 'Rò rỉ': 'prediction-high', 'Nghi ngờ cao': 'prediction-high',
      'Rò rỉ nghi ngờ trung bình': 'prediction-medium', 'Nghi ngờ trung bình': 'prediction-medium',
      'Rò rỉ nghi ngờ thấp': 'prediction-low', 'Nghi ngờ thấp': 'prediction-low',
      'Bình thường': 'prediction-normal', 'Không xác định': 'prediction-undefined'
    };
    return classMap[label] || 'prediction-unknown';
  }

  getTotalModelsCount(): number { return 2; }
  reload(): void { this.loadData(true); }
  private buildTableWithSeparateAPIs(meter: PredictiveModel): void {
    Promise.all([
      this.predictiveService.getLSTMAutoencoderPredictions(meter._id).toPromise(),
      this.predictiveService.getLSTMPredictions(meter._id).toPromise()
    ]).then(([lstmAutoencoder, lstmPredictions]) => {
      this.buildCombinedTable(meter, lstmAutoencoder || [], lstmPredictions || []);
    }).catch(error => {
      console.error('Error loading predictions:', error);
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
    if (predictions.length === 1) return predictions[0];

    const leakPredictions = predictions.filter(p => p.predicted_label === 'leak');
    const candidatePredictions = leakPredictions.length > 0 ? leakPredictions : predictions.filter(p => p.predicted_label === 'normal');
    const confidenceRank: { [key: string]: number } = { 'NNcao': 3, 'NNTB': 2, 'NNthap': 1 };

    candidatePredictions.sort((a, b) => (confidenceRank[b.confidence] || 0) - (confidenceRank[a.confidence] || 0));
    return candidatePredictions[0];
  }

  private buildCombinedTable(meter: PredictiveModel, lstmAutoencoder: any[], lstmPredictions: any[]): void {
    const formatPredictionResult = (pred: any): string => {
      if (!pred) return 'Chưa có dữ liệu';

      const label = pred.predicted_label === 'leak' ? 'Rò rỉ' :
                   pred.predicted_label === 'normal' ? 'Bình thường' : 'Không xác định';

      let confidence = 'N/A';
      if (pred.confidence && pred.confidence !== 'nan') {
        if (['NNcao', 'NNTB', 'NNthap'].includes(pred.confidence)) {
          confidence = pred.confidence;
        } else if (!isNaN(Number(pred.confidence))) {
          confidence = `${pred.confidence}%`;
        } else {
          confidence = pred.confidence;
        }
      }
      return `${label} (${confidence})`;
    };

    const models = [
      {
        name: 'LSTM',
        results: this.dates.map(dateStr => {
          const pred = lstmPredictions.find(p => this.formatDateFromPrediction(p) === dateStr);
          return formatPredictionResult(pred);
        })
      },
      {
        name: 'LSTM_AUTOENCODER',
        results: this.dates.map(dateStr => {
          const preds = lstmAutoencoder.filter(p => this.formatDateFromPrediction(p) === dateStr);
          const bestPred = preds.length > 0 ? this.selectBestPredictionForDay(preds) : null;
          return formatPredictionResult(bestPred);
        })
      },
      {
        name: 'Kết luận',
        results: this.dates.map(dateStr => this.getConclusionByDateDirect(dateStr, lstmAutoencoder, lstmPredictions))
      }
    ];

    this.tableData = { models };
  }


}
