import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DashboardService } from '../services/dashboard.service';
import { ConclusionService } from '../../../../core/services/branches/conclusion.service';
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
  private conclusionService = inject(ConclusionService);

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
      const processedData = data.map(item => ({
        ...item,
        leakDays: this.calculateLeakDays(item),
        latitude: item.latitude ?? undefined,
        longitude: item.longitude ?? undefined
      }));

      this.dashboardData.set(processedData);

      const meterIds = processedData.map(item => item._id).filter(id => id);
      this.loadConclusionsForMeters(meterIds, processedData);
    });
  }

  private loadConclusionsForMeters(meterIds: string[], processedData: Dashboard[]): void {
    this.conclusionService.getTodaysConclusionsForMeters(meterIds).subscribe({
      next: (conclusionsMap) => {
        const updatedData = processedData.map(item => ({
          ...item,
          aiConclusion: conclusionsMap[item._id] || { text: 'Chưa có dữ liệu', color: '#9e9e9e' }
        }));
        this.dashboardData.set(updatedData);
      },
      error: (error) => {
        console.error('Error loading conclusions:', error);
        const updatedData = processedData.map(item => ({
          ...item,
          aiConclusion: { text: 'Chưa có dữ liệu', color: '#9e9e9e' }
        }));
        this.dashboardData.set(updatedData);
      }
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
  private getTodayConclusionCount(type: string): number {
    const todayVN = this.formatVNDate(new Date());

    return this.dashboardData().filter(item => {
      const conclusion = this.getMeterConclusionToday(item);
      return conclusion === type;
    }).length;
  }

  private getMeterConclusionToday(item: Dashboard): string {
    if (!item || !item._id) return 'Chưa có dữ liệu';

    return (item as any).aiConclusion?.text || 'Đang tải...';
  }  private selectBestPredictionForDay(predictions: any[]): any {
    if (predictions.length === 1) return predictions[0];

    const leakPredictions = predictions.filter(p => p.predicted_label === 'leak');
    const candidatePredictions = leakPredictions.length > 0 ? leakPredictions : predictions.filter(p => p.predicted_label === 'normal');
    const confidenceRank: { [key: string]: number } = { 'NNcao': 3, 'NNTB': 2, 'NNthap': 1 };

    candidatePredictions.sort((a, b) => (confidenceRank[b.confidence] || 0) - (confidenceRank[a.confidence] || 0));
    return candidatePredictions[0];
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

    // Group predictions by date
    const predictionsByDate = new Map<string, any[]>();

    item.predictions.forEach(pred => {
      const dateRaw = (pred?.prediction_time as any)?.$date ?? pred?.prediction_time;
      const d = new Date(dateRaw);
      if (isNaN(d.getTime())) return;

      const dateStr = `${d.getDate().toString().padStart(2,'0')}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getFullYear()}`;

      if (!predictionsByDate.has(dateStr)) {
        predictionsByDate.set(dateStr, []);
      }
      predictionsByDate.get(dateStr)!.push(pred);
    });

    // Sort dates in descending order (most recent first)
    const sortedDates = Array.from(predictionsByDate.keys()).sort((a, b) => {
      const [dayA, monthA, yearA] = a.split('/').map(Number);
      const [dayB, monthB, yearB] = b.split('/').map(Number);
      const dateA = new Date(yearA, monthA - 1, dayA);
      const dateB = new Date(yearB, monthB - 1, dayB);
      return dateB.getTime() - dateA.getTime();
    });

    let leakDays = 0;

    for (const dateStr of sortedDates) {
      const dayPreds = predictionsByDate.get(dateStr) || [];

      // Create a temporary dashboard item for this date to use getMeterConclusionToday logic
      const dayItem = {
        ...item,
        predictions: dayPreds
      } as Dashboard;

      const conclusion = this.getMeterConclusionForDate(dayItem, dateStr);

      if (conclusion === 'Bình thường') {
        break;
      } else {
        leakDays++;
      }
    }

    return leakDays;
  }

  private getMeterConclusionForDate(item: Dashboard, targetDate: string): string {
    if (!item || !item.predictions) return 'Chưa có dữ liệu';

    const lstmPredictions = item.predictions.filter(p =>
      p.model_name?.toUpperCase().includes('LSTM') && !p.model_name?.toUpperCase().includes('AUTO')
    );

    const lstmAutoencoder = item.predictions.filter(p =>
      p.model_name?.toUpperCase().includes('AUTO')
    );

    const formatDate = (pred: any): string => {
      const dateRaw = (pred?.prediction_time as any)?.$date ?? pred?.prediction_time;
      const d = new Date(dateRaw);
      if (isNaN(d.getTime())) return '';
      return `${d.getDate().toString().padStart(2,'0')}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getFullYear()}`;
    };

    const lstmPred = lstmPredictions.find(p => formatDate(p) === targetDate) ?? null;
    const autoencoderPredictions = lstmAutoencoder.filter(p => formatDate(p) === targetDate);
    const autoencoderPred = autoencoderPredictions.length > 0 ? this.selectBestPredictionForDay(autoencoderPredictions) : null;

    if (!lstmPred && !autoencoderPred) return 'Chưa có dữ liệu';

    const getScore = (pred: any): number => {
      if (!pred) return 0;
      if (pred.predicted_label === 'normal') return 0;
      if (pred.predicted_label === 'leak') {
        if (pred.confidence === 'NNthap') return 1;
        if (pred.confidence === 'NNTB') return 2;
        if (pred.confidence === 'NNcao') return 3;
        return 1;
      }
      return 0;
    };

    const predictions = [lstmPred, autoencoderPred].filter(p => p !== null);
    if (predictions.length === 0) return 'Chưa có dữ liệu';

    const scores = predictions.map(pred => getScore(pred));
    const averageScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;
    const finalScore = Math.floor(averageScore);

    switch (finalScore) {
      case 0: return 'Bình thường';
      case 1: return 'Rò rỉ nghi ngờ thấp';
      case 2: return 'Rò rỉ nghi ngờ trung bình';
      case 3: return 'Rò rỉ nghi ngờ cao';
      default: return 'Bình thường';
    }
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
