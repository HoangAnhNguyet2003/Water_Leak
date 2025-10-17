import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, map, Observable, of } from 'rxjs';
import { WaterMeter } from '../models';
import { environment } from 'my-lib'
@Injectable({
  providedIn: 'root',
})
export class ClockServiceService {
  // Đếm trạng thái để hiển thị trên dashboard
  private anomalyDetectedCount = signal<number>(0);
  private onFixingCount = signal<number>(0);

  private meters$ = new BehaviorSubject<WaterMeter[]>([]);
  private readonly API_BASE = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getMeterData(force = false): Observable<WaterMeter[]> {
    if (force || this.meters$.value.length === 0) {
      this.http
        .get<{ items: any[] }>(`${this.API_BASE}/meters/get_all_meters?page_size=1000`)
        .pipe(
          map((res) => res.items.map((item) => this.mapFromApi(item))),
          catchError((err) => {
            console.error('Failed to load meters:', err);
            return of([] as WaterMeter[]);
          })
        )
        .subscribe((data) => this.meters$.next(data));
    }
    return this.meters$.asObservable();
  }

  // Cập nhật số liệu đếm từ trang thông tin đồng hồ
  public setCounts(anomalyDetected: number, onFixing: number): void {
    this.anomalyDetectedCount.set(anomalyDetected);
    this.onFixingCount.set(onFixing);
  }

  // Getter cho dashboard
  public getAnomalyDetectedCount(): number {
    return this.anomalyDetectedCount();
  }

  public getOnFixingCount(): number {
    return this.onFixingCount();
  }

  private mapFromApi(apiMeter: any): WaterMeter {

    let displayName = apiMeter.meter_name;
    if (displayName && (displayName.length === 24 || displayName === apiMeter.id)) {
      displayName = `Trạm ${apiMeter.id?.slice(-6) || 'Unknown'}`; // Lấy 6 ký tự cuối của ID
    }

    return {
      id: String(apiMeter.id),
      name: displayName || `Trạm ${apiMeter.id || 'Unknown'}`,
      branchName: apiMeter.branchName || 'Chưa xác định',
      status: apiMeter.status || 'unknown',
      installationDate: apiMeter.installation_time ? new Date(apiMeter.installation_time) : undefined,
      selected: false,
      expanded: false,
      anomalyDetected: apiMeter.anomalyDetected || 0,
    };
  }
}
