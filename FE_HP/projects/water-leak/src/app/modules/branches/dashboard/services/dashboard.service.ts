import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, map, Observable, of } from 'rxjs';
import { Dashboard } from '../models/dasboard.interface';
import { environment } from 'my-lib';

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private dashboards$ = new BehaviorSubject<Dashboard[] | null>(null);
  private readonly API_BASE = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getDashboardData(force = false): Observable<Dashboard[]> {
    if (force || !this.dashboards$.value) {
      this.http.get<{ items: any[] }>(`${this.API_BASE}/meters/get_my_meters`)
        .pipe(
          map(res => res.items.map(item => this.mapFromApi(item))),
          catchError(err => {
            console.error('Failed to load dashboard data:', err);
            return of([] as Dashboard[]);
          })
        )
        .subscribe(data => this.dashboards$.next(data));
    }

    return this.dashboards$.asObservable().pipe(map(dashboards => dashboards ?? []));
  }

  private mapFromApi(apiData: any): Dashboard {
    const parseDate = (val: any): Date | string => {
      if (!val) return '';
      if (typeof val === 'object' && val.$date) return new Date(val.$date);
      if (typeof val === 'string') return new Date(val);
      return '';
    };

    return {
      _id: String(apiData._id),
      branch_id: String(apiData.branch_id),
      meter_name: apiData.meter_name,
      selected: apiData.selected ?? false,
      expanded: apiData.expanded ?? false,
      anomalyDetected: apiData.anomalyDetected ?? undefined,
      prediction: apiData.prediction ? {
        meter_name: apiData.prediction.meter_name,
        prediction_time: parseDate(apiData.prediction.prediction_time),
        model_name: apiData.prediction.model_name ?? 'Unknown',
        predicted_label: apiData.prediction.predicted_label ?? ''
      } : null
    };
  }
}
