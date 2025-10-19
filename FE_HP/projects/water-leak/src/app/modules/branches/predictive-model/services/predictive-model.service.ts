import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, map, Observable, of } from 'rxjs';
import { PredictiveModel } from '../models';
import { SharedMeterDataService } from '../../../../core/services/branches/shared-meter-data.service';
import { environment } from 'my-lib';

@Injectable({
  providedIn: 'root'
})
export class PredictiveModelService {
  private manualMeters$ = new BehaviorSubject<PredictiveModel[] | null>(null);
  private readonly API_BASE = environment.apiUrl;

  constructor(
    private http: HttpClient,
    private sharedMeterDataService: SharedMeterDataService
  ) {}

  getManualMeters(force = false): Observable<PredictiveModel[]> {
    if (force || !this.manualMeters$.value) {
      this.sharedMeterDataService.getMeterData(force)
        .pipe(
          map(rawData => rawData.map(item => this.mapFromApi(item))),
          catchError(err => {
            console.error('Failed to load manual meters:', err);
            this.manualMeters$.next([]);
            return of([] as PredictiveModel[]);
          })
        )
        .subscribe(data => this.manualMeters$.next(data));
    }
    return this.manualMeters$.asObservable().pipe(map(meters => meters ?? []));
  }

  getLSTMAutoencoderPredictions(meterId: string): Observable<any[]> {
    const url = `${this.API_BASE}/predictions/get_lstm_autoencoder_predictions/${meterId}`;

    return this.http.get<{ predictions: any[] }>(url)
      .pipe(
        map(res => {
          return res.predictions || [];
        }),
        catchError(err => {
          console.error('Failed to load LSTM autoencoder predictions:', err);
          return of([]);
        })
      );
  }

  getLSTMPredictions(meterId: string): Observable<any[]> {
    const url = `${this.API_BASE}/predictions/get_lstm_predictions/${meterId}`;

    return this.http.get<{ predictions: any[] }>(url)
      .pipe(
        map(res => {
          return res.predictions || [];
        }),
        catchError(err => {
          console.error('Failed to load LSTM predictions:', err);
          return of([]);
        })
      );
  }

  private mapFromApi(apiMeter: any): PredictiveModel {
    const parseDate = (val: any): string | Date => {
      if (val == null) return '';
      if (typeof val === 'object') {
        if ('$date' in val) {
          const d = new Date(val.$date);
          return isNaN(d.getTime()) ? String(val.$date) : d;
        }
        if (val.$date && typeof val.$date === 'object' && val.$date.$numberLong) {
          const ms = Number(val.$date.$numberLong);
          const d = new Date(ms);
          return isNaN(d.getTime()) ? String(val.$date.$numberLong) : d;
        }
      }
      if (typeof val === 'string') {
        const d = new Date(val);
        return isNaN(d.getTime()) ? val : d;
      }
      if (val instanceof Date) return val;
      if (typeof val === 'number') {
        const d = new Date(val);
        return isNaN(d.getTime()) ? String(val) : d;
      }
      return String(val);
    };

    const predictionRaw = apiMeter.prediction ?? null;
    const prediction = predictionRaw ? {
      meter_name: predictionRaw.meter_name ?? apiMeter.meter_name ?? '',
      prediction_time: parseDate(predictionRaw.prediction_time),
      model_name: predictionRaw.model_name ?? (predictionRaw.model ? predictionRaw.model.name : '') ?? '',
      predicted_label: predictionRaw.predicted_label ?? ''
    } : null;

    const predictionsRaw = apiMeter.predictions ?? [];
    const predictions = predictionsRaw.map((pred: any) => ({
      _id: String(pred._id ?? ''),
      meter_id: String(pred.meter_id ?? ''),
      model: pred.model ? {
        _id: String(pred.model._id ?? ''),
        name: String(pred.model.name ?? '')
      } : null,
      model_name: pred.model_name ?? (pred.model ? pred.model.name : '') ?? '',
      prediction_time: parseDate(pred.prediction_time),
      predicted_threshold: pred.predicted_threshold,
      predicted_label: pred.predicted_label ?? '',
      confidence: pred.confidence ?? '',
      recorded_instant_flow: pred.recorded_instant_flow
    }));

    return {
      _id: String(apiMeter._id ?? ''),
      branch_id: String(apiMeter.branch_id ?? ''),
      meter_name: apiMeter.meter_name ?? '',
      prediction,
      predictions
    };
  }
}
