import { Component, signal, inject, OnInit } from '@angular/core';
import { catchError } from 'rxjs';
import { DashBoardData, StatCard } from '../../models';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { DashboardService } from '../../services/dashboard.service';

@Component({
  selector: 'app-dashboard-component',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard-component.component.html',
  styleUrls: ['./dashboard-component.component.scss']
})
export class DashboardComponentComponent implements OnInit {
  private router = inject(Router);
  DashboardService = inject(DashboardService);
  dashboardStats = signal<StatCard[]>([]);
  isLoading = signal<boolean>(true);

  ngOnInit(): void {
    this.isLoading.set(true);
    this.DashboardService.getDashboardData().pipe(
      catchError((err) => {
        console.error('Error fetching dashboard data:', err);
        this.isLoading.set(false);
        throw err;
      })
    ).subscribe((data) => {
      const transformedData = this.transformDashboardData(data);
      this.dashboardStats.set(transformedData);
      this.isLoading.set(false);
    });
  }

  onRefreshData(): void {
    this.isLoading.set(true);
    this.DashboardService.getDashboardData().pipe(
      catchError((err) => {
        console.error('Error refreshing dashboard data:', err);
        this.isLoading.set(false);
        throw err;
      })
    ).subscribe((data) => {
      const transformedData = this.transformDashboardData(data);
      this.dashboardStats.set(transformedData);
      this.isLoading.set(false);
    });
  }

  private transformDashboardData(data: DashBoardData[]): StatCard[] {
    if (!data || data.length === 0) return [];

    const dashboardData = data[0];
    return [
      {
        id: 'users',
        title: 'Tổng số người dùng',
        value: dashboardData.userCount,
        description: 'người dùng',
        type: 'users'
      },
      {
        id: 'meters',
        title: 'Đồng hồ hoạt động',
        value: dashboardData.activeMeterCount,
        description: 'đồng hồ',
        type: 'meters'
      },
      {
        id: 'logs',
        title: 'Log mới',
        value: dashboardData.recentLogsCount,
        description: 'bản ghi',
        type: 'logs'
      }
    ];
  }

  trackByStatId(index: number, stat: StatCard): string {
    return stat.id;
  }

  onViewDetails(stat: StatCard): void {
    console.log('View details for:', stat);
    switch (stat.type) {
      case 'users':
        this.router.navigate(['/admin/user-manager']);
        break;
      case 'meters':
        this.router.navigate(['/admin/meter-manager']);
        break;
      case 'logs':
        this.router.navigate(['/admin/logs']);
        break;
      default:
        console.log('Unknown stat type:', stat.type);
    }
  }

  getIconClass(type: string): string {
    switch (type) {
      case 'users':
        return 'fas fa-users';
      case 'meters':
        return 'fas fa-tachometer-alt';
      case 'logs':
        return 'fas fa-file-alt';
      default:
        return 'fas fa-chart-bar';
    }
  }
}
