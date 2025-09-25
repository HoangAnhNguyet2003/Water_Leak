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
}
