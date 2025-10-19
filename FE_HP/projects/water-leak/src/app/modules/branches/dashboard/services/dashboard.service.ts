import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, map, Observable, of } from 'rxjs';
import { Dashboard, PredictionDetail } from '../models/dasboard.interface';
import { SharedMeterDataService } from '../../../../core/services/branches/shared-meter-data.service';

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private dashboards$ = new BehaviorSubject<Dashboard[] | null>(null);

  constructor(
    private http: HttpClient,
    private sharedMeterDataService: SharedMeterDataService
  ) {}

  getDashboardData(force = false): Observable<Dashboard[]> {
    if (force || !this.dashboards$.value) {
      this.sharedMeterDataService.getMeterData(force)
        .pipe(
          map(rawData => rawData.map(item => this.mapFromApi(item))),
          catchError(err => {
            console.error('Failed to load dashboard data:', err);
            this.dashboards$.next([]);
            return of([] as Dashboard[]);
          })
        )
        .subscribe(data => this.dashboards$.next(data));
    }

    return this.dashboards$.asObservable().pipe(map(dashboards => dashboards ?? []));
  }

  private mapFromApi(apiData: any): Dashboard {
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

    const predictionRaw = apiData.prediction ?? null;
    const prediction = predictionRaw
      ? {
          meter_name: predictionRaw.meter_name ?? apiData.meter_name ?? '',
          prediction_time: parseDate(predictionRaw.prediction_time),
          model_name:
            predictionRaw.model_name ??
            (predictionRaw.model ? predictionRaw.model.name : '') ??
            '',
          predicted_label: predictionRaw.predicted_label ?? '',
          confidence: predictionRaw.confidence ?? ''
        }
      : null;

    const predictionsRaw = apiData.predictions ?? [];
    const predictions: PredictionDetail[] = predictionsRaw.map((pred: any) => ({
      _id: String(pred._id ?? ''),
      meter_id: String(pred.meter_id ?? ''),
      model: pred.model
        ? {
            _id: String(pred.model._id ?? ''),
            name: String(pred.model.name ?? '')
          }
        : null,
      model_name:
        pred.model_name ?? (pred.model ? pred.model.name : '') ?? null,
      prediction_time: parseDate(pred.prediction_time),
      predicted_threshold: pred.predicted_threshold,
      predicted_label: pred.predicted_label ?? '',
      confidence: pred.confidence ?? '',
      recorded_instant_flow: pred.recorded_instant_flow
    }));

    return {
      _id: String(apiData._id ?? ''),
      branch_id: String(apiData.branch_id ?? ''),
      meter_name: apiData.meter_name ?? '',
      latitude:
        apiData.latitude != null
          ? Number(apiData.latitude)
          : apiData.lat != null
          ? Number(apiData.lat)
          : undefined,
      longitude:
        apiData.longitude != null
          ? Number(apiData.longitude)
          : apiData.lng != null
          ? Number(apiData.lng)
          : undefined,
      selected: apiData.selected ?? false,
      expanded: apiData.expanded ?? false,
      anomalyDetected: apiData.anomalyDetected ?? undefined,
      prediction,
      predictions
    };
  }
}
