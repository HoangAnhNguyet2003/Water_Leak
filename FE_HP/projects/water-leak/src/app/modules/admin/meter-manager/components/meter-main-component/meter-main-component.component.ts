import { Component, computed, inject, OnInit, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MeterDropdownDetailsComponent } from '../meter-dropdown-details/meter-dropdown-details.component';
import { AddMeterFormComponent } from '../add-meter-form/add-meter-form.component';
import { MeterManagerService } from '../../services/meter-manager.service';
import { UmServicesService } from '../../../user-manager/services/um-services.service';
import { catchError } from 'rxjs';
import { SearchFilterUtils, DateUtils } from 'projects/my-lib/src/lib/utils/search-filter.utils';
import { WaterMeter, WaterMeterStatus } from '../../models/meter-manager.interface';

@Component({
  selector: 'app-meter-main-component',
  standalone: true,
  templateUrl: './meter-main-component.component.html',
  styleUrls: ['./meter-main-component.component.scss'],
  imports: [CommonModule, FormsModule, MeterDropdownDetailsComponent, AddMeterFormComponent]
})
export class MeterMainComponentComponent implements OnInit {
  meterMetaDataService = inject(MeterManagerService);
  userDataService = inject(UmServicesService);
  allMeterMetaData = signal<WaterMeter[]>([]);
  searchTerm = signal<string>('');
  selectedStatus = signal<string>('');
  activeDropdown = signal<number | null>(null);
  showAddMeterForm = signal<boolean>(false);

  filteredMeterData = computed(() => {
    const meters = this.allMeterMetaData();
    const search = this.searchTerm().toLowerCase();
    const statusFilter = this.selectedStatus();

    let result = meters;

    if (search) {
      result = result.filter(meter =>
        meter.name.toLowerCase().includes(search)
      );
    }

    if (statusFilter) {
      result = result.filter(meter => meter.status === statusFilter);
    }

    return result;
  });

  ngOnInit(): void {
    this.meterMetaDataService.getMeterData().pipe(
      catchError((err) => {
        console.error('Error fetching meter data:', err);
        throw err;
      })
    ).subscribe((data: any) => {
      this.allMeterMetaData.set(data || []);
    });
  }

  onSearchChange(searchValue: string): void {
    this.searchTerm.set(searchValue);
  }

  onStatusFilterChange(status: string): void {
    this.selectedStatus.set(status);
  }

  clearFilters(): void {
    this.searchTerm.set('');
    this.selectedStatus.set('');
  }

  getStatusLabel(status: WaterMeterStatus): string {
    switch (status) {
      case WaterMeterStatus.NORMAL:
        return 'Hoạt động';
      case WaterMeterStatus.ANOMALY:
        return 'Bất thường';
      case WaterMeterStatus.LOST_CONNECTION:
        return 'Lỗi';
      default:
        return 'Không xác định';
    }
  }

  formatInstallationDate(date?: string | Date): string {
    if (!date) return 'N/A';
    return DateUtils.formatDate(date instanceof Date ? date : new Date(date));
  }

  editMeter(meter: WaterMeter): void {
    console.log('Edit meter:', meter);
    // TODO: Implement edit meter functionality
  }

  onRemoveMeter(meter: WaterMeter): void {
    console.log('Remove meter:', meter);
    this.closeDropdown();
  this.meterMetaDataService.deleteMeter(String(meter.id)).subscribe(success => {
      if (success) {
        this.meterMetaDataService.getMeterData(true).subscribe((data: any) => {
          this.allMeterMetaData.set(data || []);
          console.log('Meter list refreshed after delete');
            try {
              this.userDataService.getAllUsers(true);
              console.log('Triggered user-manager refresh after meter delete');
            } catch (e) {
              console.error('Failed to trigger user-manager refresh:', e);
            }
        });
      } else {
        console.error('Failed to delete meter:', meter.id);
      }
    });
  }

  showAddMeterPopup(): void {
    this.showAddMeterForm.set(true);
  }

  onMeterAdded(newMeter: WaterMeter): void {
    this.meterMetaDataService.getMeterData(true).subscribe((data: any) => {
      this.allMeterMetaData.set(data || []);
      this.showAddMeterForm.set(false);
      console.log('New meter added and list refreshed:', newMeter);
    });
  }

  onAddMeterCancel(): void {
    this.showAddMeterForm.set(false);
  }

  toggleDropdown(index: number): void {
    if (this.activeDropdown() === index) {
      this.activeDropdown.set(null);
    } else {
      this.activeDropdown.set(index);
    }
  }

  closeDropdown(): void {
    this.activeDropdown.set(null);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event): void {
    if (this.activeDropdown() !== null) {
      const target = event.target as HTMLElement;
      if (!target.closest('.action-dropdown') && !target.closest('.meter-dropdown-inline')) {
        this.activeDropdown.set(null);
      }
    }
  }
}
