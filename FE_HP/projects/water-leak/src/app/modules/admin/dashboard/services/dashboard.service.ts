import { Injectable, inject } from '@angular/core';
import { Observable, of, combineLatest } from 'rxjs';
import { map } from 'rxjs/operators';
import { HttpClient } from '@angular/common/http';
import { DashBoardData } from '../models';
import { MeterManagerService } from '../../meter-manager/services/meter-manager.service';
import { UmServicesService } from '../../user-manager/services/um-services.service';
import { LogServiceService } from '../../log/services/log-service.service';
@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private uMService = inject(UmServicesService);
  private mMService = inject(MeterManagerService);
  private lService = inject(LogServiceService);

  http = inject(HttpClient);

  constructor() { }
  getDashboardData(): Observable<DashBoardData[]> {
    return combineLatest([
      this.uMService.getAllUsers(),
      this.mMService.getMeterData(),
      this.lService.getRecentLogs()
    ]).pipe(
      map(([users, meters, logs_len]) => [{
        userCount: (users || []).length,
        activeMeterCount: (meters || []).length,
        recentLogsCount: logs_len
      }])
    );
  }

}
