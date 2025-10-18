import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of, shareReplay, catchError, map } from 'rxjs';
import { environment } from 'my-lib';
import { RawMeterData } from '../../models/shared_meter.interface';
@Injectable({
  providedIn: 'root'
})
export class SharedMeterDataService {
  private meterData$ = new BehaviorSubject<RawMeterData[] | null>(null);
  private readonly API_BASE = environment.apiUrl;
  private readonly CACHE_EXPIRY_MS = 20 * 60 * 1000; 
  private lastFetched: Date | null = null;

  private sharedRequest$: Observable<RawMeterData[]> | null = null;

  constructor(private http: HttpClient) {}

  getMeterData(force = false): Observable<RawMeterData[]> {
    const cachedData = this.meterData$.value;
    const isCacheValid = this.lastFetched &&
      (Date.now() - this.lastFetched.getTime()) < this.CACHE_EXPIRY_MS;

    if (!force && cachedData && isCacheValid) {
      return of(cachedData);
    }

    if (this.sharedRequest$) {
      return this.sharedRequest$;
    }

    this.sharedRequest$ = this.http.get<{ items: any[] }>(`${this.API_BASE}/meters/get_my_meters`)
      .pipe(
        map(response => response.items || []),
        catchError(error => {
          console.error('Failed to load meter data:', error);
          return of([] as RawMeterData[]);
        }),
        shareReplay(1) 
      );

    this.sharedRequest$.subscribe({
      next: (data) => {
        this.meterData$.next(data);
        this.lastFetched = new Date();
        this.sharedRequest$ = null;
      },
      error: () => {
        this.sharedRequest$ = null;
      }
    });

    return this.sharedRequest$;
  }


  getCachedMeterData(): Observable<RawMeterData[]> {
    return this.meterData$.asObservable().pipe(
      map(data => data || [])
    );
  }


  refreshMeterData(): Observable<RawMeterData[]> {
    return this.getMeterData(true);
  }

  clearCache(): void {
    this.meterData$.next(null);
    this.lastFetched = null;
    this.sharedRequest$ = null;
  }


  isCacheValid(): boolean {
    return this.lastFetched !== null &&
           (Date.now() - this.lastFetched.getTime()) < this.CACHE_EXPIRY_MS;
  }

  getCacheStatus(): {
    hasCachedData: boolean;
    isValid: boolean;
    lastFetched: Date | null;
    itemCount: number;
  } {
    const cachedData = this.meterData$.value;
    return {
      hasCachedData: cachedData !== null,
      isValid: this.isCacheValid(),
      lastFetched: this.lastFetched,
      itemCount: cachedData?.length || 0
    };
  }

  getMeterIds(): Observable<string[]> {
    return this.getCachedMeterData().pipe(
      map(meters => meters.map(meter => meter._id).filter(id => id))
    );
  }

  getMeterById(meterId: string): Observable<RawMeterData | null> {
    return this.getCachedMeterData().pipe(
      map(meters => meters.find(meter => meter._id === meterId) || null)
    );
  }

  preloadData(): Observable<RawMeterData[]> {
    console.log('Preloading shared meter data...');
    return this.getMeterData(false);
  }
}
