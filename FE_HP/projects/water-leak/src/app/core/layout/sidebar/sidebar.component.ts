import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MenuItem } from '../../models/sidebar_data.interface';
import { AuthService } from 'my-lib';
import { Observable, of } from 'rxjs';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule],
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss']
})

export class SidebarComponent implements OnInit {
  private auth = inject(AuthService);
  private roleName = '';
  userName = signal(this.auth.getCurrentUser()?.username ?? 'Guest');
  menu$: Observable<MenuItem[]> = of([]);

  private allMenu: MenuItem[] = [
    { label: 'Dự đoán rò rỉ mô hình', icon: 'fas fa-home', route: '/branches/predictive-model', allowedRoles: ['branch'] },
    { label: 'Dự đoán rò rỉ thủ công', icon: 'fas fa-tools', route: '/branches/manual-model', allowedRoles: ['branch'] },
    { label: 'Quản lý đồng hồ nước', icon: 'fas fa-tachometer-alt', route: '/branches/meter-management', allowedRoles: ['branch'] },

    { label: 'Admin Dashboard', icon: 'fas fa-home', route: '/admin/dashboard', allowedRoles: ['admin'] },
    { label: 'Quản lý người dùng hệ thống', icon: 'fas fa-users', route: '/admin/user-manager', allowedRoles: ['admin'] },
    { label: 'Quản lý đồng hồ nước', icon: 'fas fa-chart-line', route: '/admin/meter-manager', allowedRoles: ['admin'] },
    { label: 'Quản lý log hệ thống', icon: 'fas fa-bell', route: '/admin/logs', allowedRoles: ['admin'] },
  ]

  ngOnInit(): void {
    this.roleName = this.auth.getCurrentUser()?.roleName ?? '';
    this.menu$ = of(this.allMenu.filter(item => item.allowedRoles.includes(this.roleName)));
  }

  public trackByRoute(index: number, item: MenuItem): string | number {
    return item.route ?? index;
  }
}
