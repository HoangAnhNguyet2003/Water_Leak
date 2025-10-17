import { Component, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { ClockServiceService } from '../../../water-clock/services/clock-service.service';
import { trigger, style, transition, animate } from '@angular/animations';
import { WaterMeter, WaterMeterFilter } from '../../models';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-water-meter-info',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './water-meter-info.component.html',
  styleUrls: ['./water-meter-info.component.scss'],
  animations: [
    trigger('slideInOut', [
      transition(':enter', [
        style({ height: '0', opacity: 0, overflow: 'hidden' }),
        animate('300ms ease-in-out', style({ height: '*', opacity: 1 }))
      ]),
      transition(':leave', [
        style({ height: '*', opacity: 1, overflow: 'hidden' }),
        animate('300ms ease-in-out', style({ height: '0', opacity: 0 }))
      ])
    ])
  ]
})
export class WaterMeterInfoComponent implements OnInit, OnDestroy {
  waterMeters = signal<WaterMeter[]>([]);
  filteredMeters = signal<WaterMeter[]>([]);
  filter = signal<WaterMeterFilter>({ searchTerm: '', statusFilter: '' });
  selectAll = signal<boolean>(false);

  showExportPopup = signal<boolean>(false);
  showSuccessNotification = signal<boolean>(false);

  private queryParamsSubscription?: Subscription;
  private dataSubscription?: Subscription;
  private searchTimeout: any;

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private clockService: ClockServiceService
  ) {}

  ngOnInit(): void {
    // Lấy dữ liệu từ API
    this.dataSubscription = this.clockService.getMeterData().subscribe(meters => {
      this.waterMeters.set(meters);
      this.filteredMeters.set(meters);
      this.updateCountsForDashboard();
    });

    // Xử lý query parameters từ route
    this.queryParamsSubscription = this.route.queryParams.subscribe(params => {
      const statusFilter = params['statusFilter'];
      if (statusFilter) {
        this.filter.update(current => ({
          ...current,
          statusFilter
        }));
        this.onSearch();
      }
    });
  }

  private isValidWaterMeter(meter: any): meter is WaterMeter {
    return meter &&
           typeof meter.id === 'string' &&
           typeof meter.name === 'string' &&
           typeof meter.status === 'string';
  }

  onSearch(): void {
    const currentFilter = this.filter();
    const meters = this.waterMeters();

    if (!meters || !Array.isArray(meters)) return;

    const filtered = meters.filter(meter => {
      if (!this.isValidWaterMeter(meter)) return false;

      const matchesSearch = !currentFilter.searchTerm ||
        meter.name.toLowerCase().includes(currentFilter.searchTerm.toLowerCase());
      const matchesStatus = !currentFilter.statusFilter ||
        meter.status === currentFilter.statusFilter;

      return matchesSearch && matchesStatus;
    });

    this.filteredMeters.set(filtered);
    this.updateCountsForDashboard();
  }

  onFilterChange(): void {
    this.onSearch();
  }

  onStatusFilterChange(status: string): void {
    this.filter.update(curr => ({ ...curr, statusFilter: status }));
    this.onSearch();
  }

  onSearchTermChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const value = target?.value ?? '';
    this.filter.update(curr => ({ ...curr, searchTerm: value }));
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }
    this.searchTimeout = setTimeout(() => this.onSearch(), 250);
  }

  onSelectAll(): void {
    const newSelectAll = !this.selectAll();
    this.selectAll.set(newSelectAll);

    const updatedMeters = this.filteredMeters().map(meter => ({
      ...meter,
      selected: newSelectAll
    }));
    this.filteredMeters.set(updatedMeters);
  }

  onSelectMeter(meterId: string): void {
    const updatedMeters = this.filteredMeters().map(meter =>
      meter.id === meterId ? { ...meter, selected: !meter.selected } : meter
    );
    this.filteredMeters.set(updatedMeters);
    const allSelected = updatedMeters.every(meter => meter.selected);
    this.selectAll.set(allSelected);
  }

  exportData(): void {
    this.showExportPopup.set(true);
  }

  hasSelectedMeters(): boolean {
    return this.filteredMeters().some(meter => meter.selected);
  }

  closeExportPopup(): void {
    this.showExportPopup.set(false);
  }

  confirmExport(): void {
    const selectedMeters = this.filteredMeters().filter(meter => meter.selected);
    this.showExportPopup.set(false);
    this.showSuccessNotification.set(true);
  }

  closeSuccessNotification(): void {
    this.showSuccessNotification.set(false);
  }

  getStatusClass(status: string): string {
    switch (status?.toLowerCase()) {
      case 'normal': return 'status-normal';
      case 'anomaly': return 'status-anomaly';
      case 'lost': return 'status-lost';
      case 'unknown': return 'status-unknown';
      // Legacy support
      case 'on fixing': return 'status-fixing';
      case 'anomaly detected': return 'status-anomaly';
      default: return 'status-unknown';
    }
  }

  getStatusText(status: string): string {
    switch (status?.toLowerCase()) {
      case 'normal': return 'Bình thường';
      case 'anomaly': return 'Bất thường';
      case 'lost': return 'Mất kết nối';
      case 'unknown': return 'Không xác định';
      // Legacy support
      case 'on fixing': return 'Đang sửa chữa';
      case 'anomaly detected': return 'Bất thường';
      default: return status || 'Không xác định';
    }
  }

  trackByMeterId(index: number, meter: WaterMeter): string {
    return meter.id;
  }

  toggleDetails(meterId: string): void {
    const updatedMeters = this.filteredMeters().map(meter =>
      meter.id === meterId ? { ...meter, expanded: !meter.expanded } : meter
    );
    this.filteredMeters.set(updatedMeters);

    const updatedAllMeters = this.waterMeters().map(meter =>
      meter.id === meterId ? { ...meter, expanded: !meter.expanded } : meter
    );
    this.waterMeters.set(updatedAllMeters);
  }

  viewDetails(meterId: string): void {
    this.toggleDetails(meterId);
  }

  isExpanded(meterId: string): boolean {
    const meter = this.filteredMeters().find(m => m.id === meterId);
    return meter?.expanded || false;
  }

  viewChart(meterId: string): void {
    const meter = this.filteredMeters().find(m => m.id === meterId);

    if (!meter) {
      return;
    }

    if (!this.isValidWaterMeter(meter)) {
      return;
    }

    try {
      const encodedName = encodeURIComponent(meter.name || 'Unknown');
      const navigationPath = ['/company', 'water-clock', 'chart', meterId, encodedName];

      this.router.navigate(navigationPath);
    } catch (error) {
      // Error in viewChart
    }
  }

  // Method test navigation đơn giản
  testNavigation(): void {
    this.router.navigate(['/company', 'dashboard']);
  }

  ngOnDestroy(): void {
    if (this.queryParamsSubscription) {
      this.queryParamsSubscription.unsubscribe();
    }
    if (this.dataSubscription) {
      this.dataSubscription.unsubscribe();
    }
  }

  private updateCountsForDashboard(): void {
    const all = this.waterMeters();
    const anomaly = all.filter(m => m.status === 'Anomaly detected').length;
    const fixing = all.filter(m => m.status === 'On fixing').length;
    this.clockService.setCounts(anomaly, fixing);
  }
}
