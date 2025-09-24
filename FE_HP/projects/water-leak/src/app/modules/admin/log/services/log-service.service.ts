import { LogMetaData } from './../models/log.interface';
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable as RxObservable } from 'rxjs';
import { io, Socket } from 'socket.io-client';

@Injectable({
  providedIn: 'root'
})
export class LogServiceService {

  private urlAPI = 'http://localhost:5000/api/v1';
  http = inject(HttpClient);
  private socket: Socket | null = null;
  private logObservable: RxObservable<LogMetaData> | null = null;

  getLogData() {
    return this.http.get<LogMetaData[]>(`${this.urlAPI}/logs/get_all_logs`).pipe(
      map(data => data.map(item => this.mapFromApi(item))));
  }

  connectSocket(): void {
    if (this.socket) {
      return;
    }

    this.socket = io(this.urlAPI, {
      transports: ['websocket'],
      withCredentials: true
    });

    this.logObservable = new RxObservable<LogMetaData>((subscriber) => {
      if (!this.socket) {
        subscriber.complete();
        return;
      }

      this.socket.on('connect', () => {
        console.log('socket connected', this.socket?.id);
      });

      this.socket.on('auth_ok', (payload: any) => {
        console.log('socket auth_ok', payload);
      });

      this.socket.on('auth_error', (err: any) => {
        console.error('socket auth_error', err);
      });

      this.socket.on('log', (data: any) => {
        try {
          const mapped = this.mapFromApi(data);
          subscriber.next(mapped);
        } catch (e) {
          console.error('Failed parsing log event', e);
        }
      });

      this.socket.on('disconnect', (reason: string) => {
        console.log('socket disconnected', reason);
      });

      return () => {
        if (this.socket) {
          this.socket.disconnect();
          this.socket = null;
        }
      };
    });
  }

  onLog(): RxObservable<LogMetaData> | null {
    return this.logObservable;
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
