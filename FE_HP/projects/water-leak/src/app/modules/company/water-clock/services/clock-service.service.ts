import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class ClockServiceService {
  // Đếm trạng thái để hiển thị trên dashboard
  private anomalyDetectedCount = signal<number>(0);
  private onFixingCount = signal<number>(0);

  constructor() { }

  // Cập nhật số liệu đếm từ trang thông tin đồng hồ
  public setCounts(anomalyDetected: number, onFixing: number): void {
    this.anomalyDetectedCount.set(anomalyDetected);
    this.onFixingCount.set(onFixing);
  }

  // Getter cho dashboard
  public getAnomalyDetectedCount(): number {
    return this.anomalyDetectedCount();
  }

  public getOnFixingCount(): number {
    return this.onFixingCount();
  }
}

