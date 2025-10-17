import { LogMetaData } from './../models/log.interface';
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable as RxObservable } from 'rxjs';
import { environment } from 'my-lib'

@Injectable({
  providedIn: 'root'
})
export class LogServiceService {

  private urlAPI = environment.apiUrl;
  http = inject(HttpClient);

  getLogData() {
    return this.http.get<LogMetaData[]>(`${this.urlAPI}/logs/get_all_logs`).pipe(
      map(data => data.map(item => this.mapFromApi(item))));
  }

  mapFromApi(data: any): LogMetaData {
    return {
      id: data.id,
      source: data.source,
      created_time: data.create_time,
      log_type: data.log_type,
      message: data.message
    }
  }

  getRecentLogs(): RxObservable<number> {
    return this.http.get<LogMetaData[]>(`${this.urlAPI}/logs/get_all_logs`).pipe(
      map(data => data.length)
    );
  }
  constructor() { }
}
