import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, map, Observable, of } from 'rxjs';
import { ManualModel } from '../models/manual-model.interface';
import { environment } from 'my-lib';

@Injectable({
  providedIn: 'root'
})
export class ManualMeterService {
  getMeterMeasurements(meterId: string, fromStr: string, toStr: string) {
    throw new Error('Method not implemented.');
  }
  private manualMeters$ = new BehaviorSubject<ManualModel[] | null>(null);
  private readonly API_BASE = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getManualMeters(force = false): Observable<ManualModel[]> {
    if (force || !this.manualMeters$.value) {
      this.http.get<{ items: any[] }>(`${this.API_BASE}/meters/get_my_meters`)
        .pipe(
          map(res => res.items.map(item => this.mapFromApi(item))),
          catchError(err => {
            console.error('Failed to load manual meters:', err);
            return of([] as ManualModel[]);
          })
        )
        .subscribe(data => this.manualMeters$.next(data));
    }
    return this.manualMeters$.asObservable().pipe(map(meters => meters ?? []));
  }


  private mapFromApi(apiMeter: any): ManualModel {
    const parseDate = (val: any): Date | string => {
      if (!val) return '';
      if (typeof val === 'object' && val.$date) {
        const d = new Date(val.$date);
        return isNaN(d.getTime()) ? val.$date : d;
      }
      if (typeof val === 'string') {
        const d = new Date(val);
        return isNaN(d.getTime()) ? val : d;
      }
      return '';
    };
    return {
      _id: String(apiMeter._id),
      branch_id: String(apiMeter.branch_id),
      meter_name: apiMeter.meter_name,
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
        instant_flow: Number(apiMeter.measurement.instant_flow)
      } : null,
      selected: apiMeter.selected ?? false,
      expanded: apiMeter.expanded ?? false,
      anomalyDetected: apiMeter.anomalyDetected ?? undefined
    };
  }

  setThreshold(meterId: string, thresholdValue: number): Observable<any> {
    const body = thresholdValue > 0 ? { threshold_value: thresholdValue } : {};

    return this.http.post(`${this.API_BASE}/meters/add_new_threshold/${meterId}`, body).pipe(
      catchError(err => {
        console.error('Failed to set threshold:', err);
        throw err;
      })
    );
  }

  getThresholdByDate(meterId: string, date: string): Observable<number | null> {
    return this.http.get<any>(`${this.API_BASE}/meters/threshold/${meterId}/${date}`).pipe(
      map(response => response.success ? response.threshold_value : null),
      catchError(err => {
        console.error('Failed to get threshold by date:', err);
        return of(null);
      })
    );
  }
}
