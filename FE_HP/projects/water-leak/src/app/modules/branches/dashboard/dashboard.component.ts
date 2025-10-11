import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

export interface DashboardMeter {
  id: string;
  meterName: string;
  location: string;
  leakDays: number;
  suspicionLevel: 'low' | 'medium' | 'high';
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit {
  private router = inject(Router);
  
  // Mock data for dashboard
  mockData = signal<DashboardMeter[]>([
    { id: '1', meterName: 'Đồng hồ Khu A', location: 'Khu A - Tầng 1', leakDays: 5, suspicionLevel: 'high' },
    { id: '2', meterName: 'Đồng hồ Khu B', location: 'Khu B - Tầng 2', leakDays: 4, suspicionLevel: 'high' },
    { id: '3', meterName: 'Đồng hồ Khu C', location: 'Khu C - Tầng 1', leakDays: 3, suspicionLevel: 'medium' },
    { id: '4', meterName: 'Đồng hồ Khu D', location: 'Khu D - Tầng 3', leakDays: 3, suspicionLevel: 'medium' },
    { id: '5', meterName: 'Đồng hồ Khu E', location: 'Khu E - Tầng 2', leakDays: 2, suspicionLevel: 'low' },
    { id: '6', meterName: 'Đồng hồ Khu F', location: 'Khu F - Tầng 1', leakDays: 2, suspicionLevel: 'low' },
    { id: '7', meterName: 'Đồng hồ Khu G', location: 'Khu G - Tầng 4', leakDays: 2, suspicionLevel: 'low' },
    { id: '8', meterName: 'Đồng hồ Khu H', location: 'Khu H - Tầng 2', leakDays: 2, suspicionLevel: 'low' },
    { id: '9', meterName: 'Đồng hồ Khu I', location: 'Khu I - Tầng 3', leakDays: 1, suspicionLevel: 'low' },
    { id: '10', meterName: 'Đồng hồ Khu J', location: 'Khu J - Tầng 1', leakDays: 0, suspicionLevel: 'low' },
    { id: '11', meterName: 'Đồng hồ Khu K', location: 'Khu K - Tầng 2', leakDays: 0, suspicionLevel: 'low' },
    { id: '12', meterName: 'Đồng hồ Khu L', location: 'Khu L - Tầng 4', leakDays: 0, suspicionLevel: 'low' }
  ]);

  searchTerm: string = '';

  // Logic tìm kiếm theo tên đồng hồ
  filteredData = computed(() => {
    const searchLower = this.searchTerm.toLowerCase().trim();
    if (!searchLower) return this.mockData();
    
    return this.mockData().filter(item => {
      const meterName = item.meterName.toLowerCase();
      const location = item.location.toLowerCase();
      
      // Tìm kiếm theo tên đồng hồ hoặc vị trí
      return meterName.includes(searchLower) || location.includes(searchLower);
    });
  });

  totalLow = computed(() => {
    return this.mockData().filter(item => item.suspicionLevel === 'low').length;
  });

  totalMedium = computed(() => {
    return this.mockData().filter(item => item.suspicionLevel === 'medium').length;
  });

  totalHigh = computed(() => {
    return this.mockData().filter(item => item.suspicionLevel === 'high').length;
  });

  ngOnInit(): void {
    // Initialize dashboard data
  }

  onSearchChange(): void {
    // Search is handled by computed signal
  }

  trackByFn(index: number, item: DashboardMeter): string {
    return item.id;
  }

  getLeakDaysClass(leakDays: number): string {
    if (leakDays >= 4) return 'leak-days-high';
    if (leakDays >= 2) return 'leak-days-medium';
    return 'leak-days-low';
  }

  navigateToMeters(level: 'low' | 'medium' | 'high'): void {
    this.router.navigate(['/branches/meter-management'], { queryParams: { suspicion: level } });
  }
}
