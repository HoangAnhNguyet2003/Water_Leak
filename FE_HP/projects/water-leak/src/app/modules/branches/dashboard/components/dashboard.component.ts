import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DashboardService } from '../services/dashboard.service';
import { Dashboard } from '../models/dasboard.interface';
import * as L from 'leaflet';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit {
  private router = inject(Router);
  private dashboardService = inject(DashboardService);

  dashboardData = signal<Dashboard[]>([]);
  searchTerm = signal<string>('');

  filteredData = computed(() => {
    const term = this.normalizeString(this.searchTerm());
    const data = this.dashboardData();

    return data
      .filter(item => {
        if (!term) return true;
        const meterName = this.normalizeString(item.meter_name || '');
        return meterName.includes(term);
      })
      .map(item => ({
        ...item,
        leakDays: this.calculateLeakDays(item)
      }));
  });

  totalLow = computed(() => this.getTodayConclusionCount('Rò rỉ nghi ngờ thấp'));
  totalMedium = computed(() => this.getTodayConclusionCount('Rò rỉ nghi ngờ trung bình'));
  totalHigh = computed(() => this.getTodayConclusionCount('Rò rỉ nghi ngờ cao'));

  showMap = false;
  private map: L.Map | null = null;
  private selectedItem: Dashboard | null = null;

  ngOnInit(): void {
    this.dashboardService.getDashboardData(true).subscribe(data => {
      this.dashboardData.set(
        data.map(item => ({
          ...item,
          leakDays: this.calculateLeakDays(item),
          latitude: item.latitude ?? undefined,
          longitude: item.longitude ?? undefined
        }))
      );
    });
  }

  private normalizeString(str: string): string {
    return str.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
  }

  onSearchChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.searchTerm.set(target.value);
  }
  private formatVNDate(date: Date): string {
    const vnTime = new Date(date.toLocaleString('en-US', { timeZone: 'Asia/Ho_Chi_Minh' }));
    const day = vnTime.getDate().toString().padStart(2, '0');
    const month = (vnTime.getMonth() + 1).toString().padStart(2, '0');
    const year = vnTime.getFullYear();
    return `${day}/${month}/${year}`;
  }
// kết luận từ đây
  private getConclusion(item: Dashboard): string {
    const pred = item.prediction;
    if (!pred) return 'Chưa có dữ liệu';

    const label = (pred.predicted_label ?? '').trim();
    const conf = (pred.confidence ?? '').toString();
    const directLabels = ['NNthap', 'NNTB', 'NNcao'];

    if (directLabels.includes(label)) {
      if (label === 'NNcao') return 'Rò rỉ nghi ngờ cao';
      if (label === 'NNTB') return 'Rò rỉ nghi ngờ trung bình';
      return 'Rò rỉ nghi ngờ thấp';
    }

    if (label === 'normal') return 'Bình thường';
    if (label === 'leak') {
      if (directLabels.includes(conf)) {
        if (conf === 'NNcao') return 'Rò rỉ nghi ngờ cao';
        if (conf === 'NNTB') return 'Rò rỉ nghi ngờ trung bình';
        return 'Rò rỉ nghi ngờ thấp';
      }
      const num = Number(conf);
      if (!isNaN(num)) {
        if (num >= 75) return 'Rò rỉ nghi ngờ cao';
        if (num >= 40) return 'Rò rỉ nghi ngờ trung bình';
        return 'Rò rỉ nghi ngờ thấp';
      }
      return 'Rò rỉ nghi ngờ thấp';
    }

    return 'Không xác định';
  }


  private getTodayConclusionCount(type: string): number {
    const todayVN = this.formatVNDate(new Date()); 

    const result = this.dashboardData()
      .flatMap(item =>
        (item.predictions ?? []).map(pred => ({
          meter_name: item.meter_name,
          prediction_time: pred.prediction_time,
          predicted_label: pred.predicted_label,
          confidence: pred.confidence
        }))
      )
      .filter(pred => {
        if (!pred.prediction_time) return false;

        const vnDate = this.formatVNDate(new Date(pred.prediction_time));

        const conclusion = this.getConclusion({
          prediction: {
            meter_name: pred.meter_name,
            prediction_time: pred.prediction_time,
            model_name: '',
            predicted_label: pred.predicted_label,
            confidence: pred.confidence
          }
        } as Dashboard);

        return vnDate === todayVN && conclusion === type;
      });

    return result.length;
  }

  
  getTodayConclusionsSummary(): { low: number; medium: number; high: number } {
    const todayVN = this.formatVNDate(new Date());
    let low = 0, medium = 0, high = 0;

    this.dashboardData().forEach(item => {
      const predictions = item.predictions ?? [];
      predictions.forEach(pred => {
        const vnDate = this.formatVNDate(new Date(pred.prediction_time));
        if (vnDate !== todayVN) return;

        const conclusion = this.getConclusion({
          prediction: {
            meter_name: item.meter_name,
            prediction_time: pred.prediction_time,
            model_name: '',
            predicted_label: pred.predicted_label,
            confidence: pred.confidence
          }
        } as Dashboard);

        if (conclusion === 'Rò rỉ nghi ngờ thấp') low++;
        else if (conclusion === 'Rò rỉ nghi ngờ trung bình') medium++;
        else if (conclusion === 'Rò rỉ nghi ngờ cao') high++;
      });
    });

    return { low, medium, high };
  }
 // Tính số ngày rò rỉ 
 getLeakDaysClass(leakDays: number): string {
    if (leakDays >= 4) return 'leak-days-high';
    if (leakDays >= 2) return 'leak-days-medium';
    return 'leak-days-low';
  }

  navigateToMeters(level: 'NNthap' | 'NNTB' | 'NNcao'): void {
    this.router.navigate(['/branches/meter-management'], { queryParams: { statusFilter: level } });
  }

  private calculateLeakDays(item: Dashboard): number {
  if (!item.predictions || item.predictions.length === 0) return 0;
  const sortedPreds = item.predictions
    .filter(p => p.prediction_time)
    .sort((a, b) => new Date(b.prediction_time).getTime() - new Date(a.prediction_time).getTime());

  let leakDays = 0;

  for (const pred of sortedPreds) {
    const conclusion = this.getConclusion({
      prediction: {
        meter_name: item.meter_name,
        prediction_time: pred.prediction_time,
        model_name: '',
        predicted_label: pred.predicted_label,
        confidence: pred.confidence
      }
    } as Dashboard);

    if (conclusion === 'Bình thường') {
      break;
    } else {
      leakDays++;
    }
  }
  return leakDays;
}

  //Hiển thị bản đồ 
  showMapForItem(item: Dashboard): void {
    this.selectedItem = item;
    this.showMap = true;
    setTimeout(() => this.initMap(), 300);
  }

  closeMap(): void {
    this.showMap = false;
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }

  private initMap(): void {
    const defaultLat = 20.8443;
    const defaultLng = 106.6881;
    const latitude = this.selectedItem?.latitude ?? defaultLat;
    const longitude = this.selectedItem?.longitude ?? defaultLng;
    const hasCoords = !!(this.selectedItem?.latitude && this.selectedItem?.longitude);

    const mapContainer = document.getElementById('map');
    if (!mapContainer) {
      console.warn('⚠️ Không tìm thấy phần tử #map, thử lại...');
      setTimeout(() => this.initMap(), 200);
      return;
    }

    if (this.map) {
      this.map.remove();
      this.map = null;
    }

    this.map = L.map(mapContainer, {
      center: [latitude, longitude],
      zoom: hasCoords ? 17 : 13
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(this.map);

    if (hasCoords) {
      L.circle([latitude, longitude], {
        radius: 8,
        color: 'blue',
        fillColor: 'lightblue',
        fillOpacity: 0.5
      })
        .addTo(this.map)
        .bindPopup(`<b>${this.selectedItem?.meter_name}</b><br>(${latitude}, ${longitude})`)
        .openPopup();
    }
  }

  trackByFn(index: number, item: Dashboard): string {
    return item._id;
  }
}
