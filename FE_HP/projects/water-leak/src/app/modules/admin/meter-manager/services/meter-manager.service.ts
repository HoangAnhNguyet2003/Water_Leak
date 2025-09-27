import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, map, Observable, of } from 'rxjs';
import { WaterMeter, WaterMeterStatus } from '../models/meter-manager.interface';
import { environment } from 'projects/my-lib/src/lib/enviroments/enviroment';

@Injectable({
  providedIn: 'root'
})
export class MeterManagerService {
  private meters$ = new BehaviorSubject<WaterMeter[] | null>(null);
  private readonly API_BASE = environment.apiUrl;

  constructor(private http: HttpClient) { }

  getMeterData(force = false): Observable<any> {
    if (force || !this.meters$.value) {
      this.http.get<{ items: any[] }>(`${this.API_BASE}/meters/get_all_meters`)
        .pipe(map(res => res.items.map(item => this.mapFromApi(item))),
        catchError(err => {
                console.error('Failed to load meters:', err);
                return of([] as WaterMeter[]);
              }))
        .subscribe(data => this.meters$.next(data));
    }
    return this.meters$.asObservable();
  }

  addMeter(payload: { branch_name?: string | null, meter_name: string, installation_time?: string | null }): Observable<WaterMeter | null> {
    return this.http.post<any>(`${this.API_BASE}/meters/create`, payload).pipe(
      map(res => {
        // backend returns created meter object directly
        const newMeter = this.mapFromApi(res);
        const currentMeters = this.meters$.value || [];
        this.meters$.next([...currentMeters, newMeter]);
        return newMeter;
      }),
      catchError(err => {
        console.error('Failed to add meter:', err);
        return of(null);
      })
    );
  }

  deleteMeter(meterId: string) : Observable<boolean> {
    return this.http.delete<{ success: boolean }>(`${this.API_BASE}/meters/delete/${meterId}`)
      .pipe(
        map(response => {
          if (response.success) {
            const currentMeters = this.meters$.value || [];
            this.meters$.next(currentMeters.filter(m => m.id !== meterId));
            return true;
          }
          return false;
        }),
        catchError(err => {
          console.error('Failed to delete meter:', err);
          return of(false);
        })
      );
  }

  private mapFromApi(apiMeter: any): WaterMeter {
      return {
        id: String(apiMeter.id),
        name: apiMeter.meter_name,
        branchName: apiMeter.branchName,
        status: apiMeter.status ? apiMeter.status as WaterMeterStatus : WaterMeterStatus.NORMAL,
        installationDate: apiMeter.installation_time ? new Date(apiMeter.installation_time) : undefined,
      };
  }
}
