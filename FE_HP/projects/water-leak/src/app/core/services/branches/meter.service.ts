import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class MeterService {

  constructor() { }

  getMeters(): Observable<any[]> {
    const data = [
      { name: 'Văn Đẩu 8', status: 'Normal', installDate: '03/10/2022', manualThreshold: 100 },
    { name: 'Văn Đẩu 9', status: 'On fixing', installDate: '05/10/2022', manualThreshold: 150 },
    { name: 'Văn Đẩu 10', status: 'Normal', installDate: '01/10/2022', manualThreshold: 200 }
    ];
    return of(data);
  }
}
