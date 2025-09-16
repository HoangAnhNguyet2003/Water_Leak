import { Injectable, inject } from '@angular/core';
import { Observable, of, combineLatest } from 'rxjs';
import { map } from 'rxjs/operators';
import { HttpClient } from '@angular/common/http';
import { DashBoardData } from '../models';
import { MeterManagerService } from '../../meter-manager/services/meter-manager.service';
import { UmServicesService } from '../../user-manager/services/um-services.service';
@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private uMService = inject(UmServicesService);
  private mMService = inject(MeterManagerService);
  http = inject(HttpClient);

  constructor() { }
  getDashboardData(): Observable<DashBoardData[]> {
    return combineLatest([
      this.uMService.getAllUsers(),
      this.mMService.getMeterData()
    ]).pipe(
      map(([users, meters]) => [{
        userCount: (users || []).length,
        activeMeterCount: (meters || []).length,
        recentLogsCount: 5
      }])
    );
  }

}
