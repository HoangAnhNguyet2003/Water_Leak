import { Component, OnInit, OnDestroy, signal, WritableSignal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { trigger, style, transition, animate } from '@angular/animations';
import { BreakHistory, BreakHistoryFilter } from '../../models';
import { RepairService } from '../../services/repair.service';

@Component({
  selector: 'app-break-history',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './break-history.component.html',
  styleUrls: ['./break-history.component.scss'],
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
export class BreakHistoryComponent implements OnInit, OnDestroy {
  breakHistories = signal<BreakHistory[]>([]);
  filter: WritableSignal<BreakHistoryFilter> = signal({
    searchTerm: ''
  });
  selectAll = signal(false);
  
  private searchTimeout: any;

  constructor(private repairService: RepairService) {}

  ngOnInit(): void {
    this.loadData();
  }

  ngOnDestroy(): void {
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }
  }

  /** Load dữ liệu từ service */
  private loadData(): void {
    this.repairService.getRepairs().subscribe(data => {
      const initialized = data.map(h => ({
        ...h,
        expanded: false,
        selected: false
      }));
      this.breakHistories.set(initialized);
    });
  }

  /** Debounce tìm kiếm */
  onSearchTermChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const value = target?.value ?? '';
    this.filter.update(f => ({ ...f, searchTerm: value }));

    if (this.searchTimeout) clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => {
      this.updateSelectAllState();
    }, 250);
  }

  /** Getter danh sách đã lọc */
  filteredHistories(): BreakHistory[] {
    const { searchTerm } = this.filter();
    let filtered = this.breakHistories();

    if (searchTerm) {
      const keyword = searchTerm.toLowerCase();
      filtered = filtered.filter(
        h =>
          (h.meterName && h.meterName.toLowerCase().includes(keyword)) ||
          (h.leakReason && h.leakReason.toLowerCase().includes(keyword))
      );
    }

    return filtered;
  }

  /** Chọn tất cả trong danh sách lọc */
  onSelectAll(): void {
    const newValue = !this.selectAll();
    this.selectAll.set(newValue);

    const filteredIds = this.filteredHistories().map(h => h.id);

    const updated = this.breakHistories().map(h =>
      filteredIds.includes(h.id) ? { ...h, selected: newValue } : h
    );

    this.breakHistories.set(updated);
  }

  /** Chọn từng item */
  onItemSelect(historyId: string): void {
    const updated = this.breakHistories().map(h =>
      h.id === historyId ? { ...h, selected: !h.selected } : h
    );
    this.breakHistories.set(updated);

    this.updateSelectAllState();
  }

  /** Cập nhật trạng thái selectAll theo danh sách lọc */
  private updateSelectAllState(): void {
    const list = this.filteredHistories();
    const allSelected = list.length > 0 && list.every(h => h.selected);
    this.selectAll.set(allSelected);
  }

  /** Toggle chi tiết */
  viewDetails(historyId: string): void {
    const updated = this.breakHistories().map(h =>
      h.id === historyId ? { ...h, expanded: !h.expanded } : h
    );
    this.breakHistories.set(updated);
  }

  /** TrackBy để tối ưu render */
  trackByHistoryId(index: number, history: BreakHistory): string {
    return history.id;
  }

  /** Xuất dữ liệu */
  exportData(): void {
    const selected = this.breakHistories().filter(h => h.selected);
    console.log('Xuất dữ liệu lịch sử vỡ:', selected);
    // TODO: Gọi service export hoặc download file CSV/Excel
  }
}
