import { Injectable } from '@angular/core';
import { DashBoardData, DashBoardDataStatus } from '../models';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, map, Observable, of } from 'rxjs';
import { environment } from 'my-lib'

@Injectable({
  providedIn: 'root'
})
export class DashboardMainServiceService {
  private meters$ = new BehaviorSubject<DashBoardData[] | null>(null);
    private readonly API_BASE = environment.apiUrl;

    constructor(private http: HttpClient) { }

    getMeterData(force = false): Observable<any> {
      if (force || !this.meters$.value) {
        this.http.get<{ items: any[] }>(`${this.API_BASE}/meters/get_all_meters`)
          .pipe(map(res => res.items.map(item => this.mapFromApi(item))),
          catchError(err => {
                  console.error('Failed to load meters:', err);
                  return of([] as DashBoardData[]);
                }))
          .subscribe(data => this.meters$.next(data));
      }
      return this.meters$.asObservable();
    }


 private mapFromApi(apiMeter: any): DashBoardData {
      return {
        id: String(apiMeter.id),
        name: apiMeter.meter_name,
        branchName: apiMeter.branchName,
        status: apiMeter.status ? apiMeter.status as DashBoardDataStatus : DashBoardDataStatus.NORMAL,
        installationDate: apiMeter.installation_time ? new Date(apiMeter.installation_time) : undefined,
        meter_data: {
          id: String(apiMeter.id),
          name: apiMeter.meter_name,
          status: apiMeter.status ? apiMeter.status as DashBoardDataStatus : DashBoardDataStatus.NORMAL
        }
      };
  }
}
