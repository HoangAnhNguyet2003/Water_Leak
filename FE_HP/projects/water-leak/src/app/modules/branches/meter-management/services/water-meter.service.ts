import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, map, Observable, of } from 'rxjs';
import { WaterMeter } from '../models/water-meter.interface';

@Injectable({
  providedIn: 'root'
})
export class WaterMeterService {
  private meters$ = new BehaviorSubject<WaterMeter[] | null>(null);
  private readonly API_BASE = 'http://localhost:5000/api/v1';

  constructor(private http: HttpClient) { }

  getMyMeters(force = false): Observable<WaterMeter[]> {
    if (force || !this.meters$.value) {
      this.http.get<{ items: any[] }>(`${this.API_BASE}/meters/get_my_meters`)
        .pipe(
          map(res => res.items.map(item => this.mapFromApi(item))),
          catchError(err => {
            console.error('Failed to load meters:', err);
            return of([] as WaterMeter[]);
          })
        )
        .subscribe(data => this.meters$.next(data));
    }

    return this.meters$.asObservable().pipe(map(meters => meters ?? []));
  }

  private mapFromApi(apiMeter: any): WaterMeter {
    const parseDate = (val: any): Date | string => {
      if (!val) return '';
      if (typeof val === 'object' && val.$date) return new Date(val.$date);
      if (typeof val === 'string') return new Date(val);
      return '';
    };

    return {
      _id: String(apiMeter._id),
      branch_id: String(apiMeter.branch_id),
      meter_name: apiMeter.meter_name,
      installation_time: parseDate(apiMeter.installation_time),
      branchName: apiMeter.branchName,
      threshold: apiMeter.threshold ? {
        id: String(apiMeter.threshold.id),
        meter_id: String(apiMeter.threshold.meter_id),
        set_time: parseDate(apiMeter.threshold.set_time),
        threshold_value: Number(apiMeter.threshold.threshold_value)
      } : null,
      measurement: apiMeter.measurement ? {
        id: String(apiMeter.measurement.id),
        meter_id: String(apiMeter.measurement.meter_id),
        measurement_time: parseDate(apiMeter.measurement.measurement_time),
        instant_flow: Number(apiMeter.measurement.instant_flow),
        instant_pressure: Number(apiMeter.measurement.instant_pressure)
      } : null,
      repair: apiMeter.repair ? {
        _id: String(apiMeter.repair._id),
        meter_id: String(apiMeter.repair.meter_id),
        recorded_time: parseDate(apiMeter.repair.recorded_time).toString(),
        repair_time: parseDate(apiMeter.repair.repair_time).toString(),
        leak_reason: apiMeter.repair.leak_reason ?? undefined,
      } : null,
      selected: apiMeter.selected ?? false,
      expanded: apiMeter.expanded ?? false,
      anomalyDetected: apiMeter.anomalyDetected ?? undefined,
      prediction: apiMeter.prediction ? {
        meter_name: apiMeter.meter_name,
        prediction_time: parseDate(apiMeter.prediction.prediction_time) ?? '',
        model_name: apiMeter.prediction.model_name ?? 'Không rõ',
        predicted_label: apiMeter.prediction.predicted_label ?? ''
      } : null
    };
  }
}
