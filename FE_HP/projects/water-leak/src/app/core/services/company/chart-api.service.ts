import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, catchError, of } from 'rxjs';
import { ChartData, ChartType } from '../../models/chart-data.interface';

interface RangeResponseItem { timestamp: string; flow: number; predicted_flow?: number | null; is_anomaly?: boolean; confidence?: number; status?: string; predicted_label?: string }
interface RangeResponse { meter_id: number; start: string; end: string; items: RangeResponseItem[] }

@Injectable({ providedIn: 'root' })
export class ChartApiService {
  private readonly API_BASE = 'http://localhost:5000/api/v1';

  constructor(private http: HttpClient) {}
  public getInstantFlowRange(meterId: number | string, hours = 4): Observable<ChartData> {
    const idStr = String(meterId);
    return this.http.get<RangeResponse>(`${this.API_BASE}/measurements/${encodeURIComponent(idStr)}/range?hours=${hours}`).pipe(
      map(res => {
        const points = (res.items || []).map(i => {
          let label = i.timestamp;
          try {
            const d = new Date(i.timestamp);
            if (!isNaN(d.getTime())) {
              const hh = String(d.getHours()).padStart(2, '0');
              const mm = String(d.getMinutes()).padStart(2, '0');
              label = `${hh}:${mm}`;
            }
          } catch (e) {}
          return { timestamp: label, value: Number(i.flow), predictedValue: null };
        });

        const chartData: ChartData = {
          meterId: res.meter_id ?? idStr,
          meterName: `Meter ${res.meter_id ?? idStr}`,
          config: {
            title: `Lưu lượng ${res.meter_id ?? idStr}`,
            subtitle: `Dữ liệu ${hours} giờ gần nhất`,
            yAxisLabel: 'Lưu lượng (m³/h)',
            xAxisLabel: 'Thời gian',
            legend: [{ label: 'Lưu lượng', color: '#4285f4' }]
          },
          data: points
        };

        return chartData;
      }),
      catchError(err => {
        console.error('Failed to load instant flow range', err);
        const empty: ChartData = {
          meterId: idStr,
          meterName: `Meter ${idStr}`,
          config: { title: `Lưu lượng ${idStr}`, legend: [{ label: 'Lưu lượng', color: '#4285f4' }] } as any,
          data: []
        } as ChartData;
        return of(empty);
      })
    );
  }

    public getInstantFlowRangeWithPredictions(meterId: number | string, hours = 4): Observable<ChartData> {
      const idStr = String(meterId);
      return this.http.get<RangeResponse>(`${this.API_BASE}/measurements/${encodeURIComponent(idStr)}/range_with_predictions?hours=${hours}`).pipe(
        map(res => {
          const points = (res.items || []).map(i => {
            let label = i.timestamp;
            try {
              const d = new Date(i.timestamp);
              if (!isNaN(d.getTime())) {
                const hh = String(d.getHours()).padStart(2, '0');
                const mm = String(d.getMinutes()).padStart(2, '0');
                label = `${hh}:${mm}`;
              }
            } catch (e) {}
            return {
              timestamp: label,
              value: Number(i.flow),
                predictedValue: i.predicted_flow !== undefined ? Number(i.predicted_flow) : null,
                isAnomaly: !!i.is_anomaly,
                confidence: i.confidence !== undefined ? Number(i.confidence) : 0,
                predictedLabel: i.status ?? i.predicted_label ?? null
            };
          });

          const config = {
            title: `Lưu lượng ${res.meter_id}`,
            subtitle: `Dữ liệu ${hours} giờ gần nhất (kèm dự đoán)` ,
            yAxisLabel: 'Lưu lượng (m³/h)',
            xAxisLabel: 'Thời gian',
            legend: [ { label: 'Lưu lượng', color: '#4285f4' } ]
          };

          const chartData: ChartData = {
            meterId: res.meter_id,
            meterName: `Meter ${res.meter_id}`,
            config,
            data: points
          };

          return chartData;
        }),
        catchError(err => {
          console.error('Failed to load instant flow range with predictions', err);
          const empty: ChartData = {
            meterId: idStr,
            meterName: `Meter ${idStr}`,
            config: { title: `Lưu lượng ${idStr}`, legend: [{ label: 'Lưu lượng', color: '#4285f4' }] },
            data: []
          } as ChartData;
          return of(empty);
        })
      );
    }
}
