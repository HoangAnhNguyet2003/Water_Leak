import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DashboardService } from '../services/dashboard.service';
import { Dashboard } from '../models/dasboard.interface';

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
  searchTerm: string = '';

  // Logic tìm kiếm theo tên đồng hồ
  filteredData = computed(() => {
    return this.dashboardData().map(item => ({
      ...item,
      location: item.location || 'nan',
      leakDays: this.calculateLeakDays(item)
    }));
  });

  totalLow = computed(() => {
    return this.dashboardData().filter(item => item.prediction?.predicted_label === 'NNthap').length;
  });

  totalMedium = computed(() => {
    return this.dashboardData().filter(item => item.prediction?.predicted_label === 'NNTB').length;
  });

  totalHigh = computed(() => {
    return this.dashboardData().filter(item => item.prediction?.predicted_label === 'NNcao').length;
  });

  ngOnInit(): void {
    this.dashboardService.getDashboardData(true).subscribe(data => {
      this.dashboardData.set(
        data.map(item => ({
          ...item,
          location: '0',
          leakDays: this.calculateLeakDays(item)
        }))
      );
    });
  }

  onSearchChange(): void {
  }

  trackByFn(index: number, item: Dashboard): string {
    return item._id;
  }

  getLeakDaysClass(leakDays: number): string {
    if (leakDays >= 4) return 'leak-days-high';
    if (leakDays >= 2) return 'leak-days-medium';
    return 'leak-days-low';
  }

  navigateToMeters(level: 'NNthap' | 'NNTB' | 'NNcao'): void {
    this.router.navigate(['/branches/meter-management'], { queryParams: { statusFilter: level } });
  }

  private calculateLeakDays(item: Dashboard): number {
    if (!item.prediction || !item.prediction.prediction_time) return 0;

    const predictionDate = new Date(item.prediction.prediction_time);
    const today = new Date();

    if (item.prediction.predicted_label === 'NNTB' || item.prediction.predicted_label === 'NNcao') {
      return Math.floor((today.getTime() - predictionDate.getTime()) / (1000 * 60 * 60 * 24));
    }

    return 0;
  }
}
