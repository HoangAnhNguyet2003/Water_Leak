import { LogMetaData } from './../models/log.interface';
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs/internal/Observable';
import { of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LogServiceService {

  private urlAPI = '';
  http = inject(HttpClient);

  getLogData() {
    return this.http.get<LogMetaData[]>(this.urlAPI);
  }
  constructor() { }
}
