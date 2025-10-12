import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, map, Observable, of } from 'rxjs';
import { BreakHistory } from '../models';
import { environment } from 'my-lib'

@Injectable({
  providedIn: 'root'
})
export class RepairService {
  private repairs$ = new BehaviorSubject<BreakHistory[]>([]);
  private readonly API_BASE = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Lấy danh sách repairs
  getRepairs(force = false): Observable<BreakHistory[]> {
    if (force || this.repairs$.value.length === 0) {
      this.http
        .get<{ items: any[] }>(`${this.API_BASE}/repairs/get_all_repairs`)
        .pipe(
          map(res => res.items.map(item => this.mapFromApi(item))),
          catchError(err => {
            console.error('Failed to load repairs:', err);
            return of([] as BreakHistory[]);
          })
        )
        .subscribe(data => this.repairs$.next(data));
    }
    return this.repairs$.asObservable();
  }

  // Mapping từ API -> BreakHistory
  private mapFromApi(apiRepair: any): BreakHistory {
    return {
      id: String(apiRepair.id),
      meterId: apiRepair.meterId ?? '',
      meterName: apiRepair.meterName ?? '', // Include meter name
      recordedTime: apiRepair.recordedTime  ,
      repairTime: apiRepair.repairTime ,
      leakReason: apiRepair.leakReason ?? '',
      leakFix: apiRepair.leakFix ?? '',
      replacementLocation: apiRepair.replacementLocation ?? '',
      replacementType: apiRepair.replacementType ?? '',
      selected: false,
      expanded: false
    };
  }
}
