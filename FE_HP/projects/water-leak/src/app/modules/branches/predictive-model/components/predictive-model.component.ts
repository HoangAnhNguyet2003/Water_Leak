import { Component, OnInit } from '@angular/core';
import { PredictiveModelService } from '../services/predictive-model.service';
import { ConclusionService } from '../../../../core/services/branches/conclusion.service';
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

  constructor(
    private predictiveService: PredictiveModelService,
    private conclusionService: ConclusionService
  ) {}

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

  private getConclusionByDate(meterId: string, dateStr: string): Promise<string> {
    return new Promise((resolve) => {
      this.conclusionService.getConclusionForMeterAndDate(meterId, dateStr).subscribe({
        next: (result) => {
          resolve(result.text);
        },
        error: (error) => {
          console.error('Error getting conclusion:', error);
          resolve('Chưa có dữ liệu');
        }
      });
    });
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
        results: []
      }
    ];

    const conclusionPromises = this.dates.map(dateStr =>
      this.getConclusionByDate(meter._id, dateStr)
    );

    Promise.all(conclusionPromises).then(conclusions => {
      models[2].results = conclusions;
      this.tableData = { models };
    }).catch(error => {
      console.error('Error getting conclusions:', error);
      models[2].results = this.dates.map(() => 'Chưa có dữ liệu');
      this.tableData = { models };
    });
  }


}
