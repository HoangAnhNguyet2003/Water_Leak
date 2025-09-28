import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, map, Observable, of } from 'rxjs';
import { PredictiveModel } from '../models';

@Injectable({
  providedIn: 'root'
})
export class PredictiveModelService {
  // Nếu cần dùng sau, vẫn giữ stub; nếu không thì xóa hoặc implement đầy đủ
  getMeterMeasurements(meterId: string, fromStr: string, toStr: string) {
    throw new Error('Method not implemented.');
  }

  private manualMeters$ = new BehaviorSubject<PredictiveModel[] | null>(null);
  private readonly API_BASE = 'http://localhost:5000/api/v1';

  constructor(private http: HttpClient) {}

  getManualMeters(force = false): Observable<PredictiveModel[]> {
    if (force || !this.manualMeters$.value) {
      this.http.get<{ items: any[] }>(`${this.API_BASE}/meters/get_my_meters`)
        .pipe(
          map(res => (res.items || []).map(item => this.mapFromApi(item))),
          catchError(err => {
            console.error('Failed to load manual meters:', err);
            // đảm bảo subject không để null nếu lỗi xảy ra
            this.manualMeters$.next([]);
            return of([] as PredictiveModel[]);
          })
        )
        .subscribe(data => this.manualMeters$.next(data));
    }
    // trả về Observable luôn có mảng (không null)
    return this.manualMeters$.asObservable().pipe(map(meters => meters ?? []));
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

    return {
      _id: String(apiMeter._id ?? ''),
      branch_id: String(apiMeter.branch_id ?? ''),
      meter_name: apiMeter.meter_name ?? '',
      prediction
    };
  }
}
