import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WaterMeter, WaterMeterStatus } from '../../models/meter-manager.interface';
import { DateUtils } from 'projects/my-lib/src/lib/utils/search-filter.utils';
import { PopupConfirmComponent, PopupMode } from 'projects/my-lib/src/lib/components';

@Component({
  selector: 'app-meter-dropdown-details',
  standalone: true,
  imports: [CommonModule, PopupConfirmComponent],
  templateUrl: './meter-dropdown-details.component.html',
  styleUrls: ['./meter-dropdown-details.component.scss']
})
export class MeterDropdownDetailsComponent {
  @Input() meter!: WaterMeter;
  @Input() isVisible = false;
  @Output() removeMeter = new EventEmitter<WaterMeter>();
  @Output() close = new EventEmitter<void>();

  showPopup = false;
  popupMode = PopupMode.CONFIRM;
  popupTitle = '';
  popupMessage = '';

  PopupMode = PopupMode;

  onRemoveMeter(): void {
    this.popupMode = PopupMode.CONFIRM;
    this.popupTitle = 'Xác nhận xóa đồng hồ nước';
    this.popupMessage = 'Bạn có chắc chắn muốn xóa đồng hồ nước này không? Hành động này không thể hoàn tác.';
    this.showPopup = true;
  }

  onPopupConfirm(data?: any): void {
    if (this.popupMode === PopupMode.CONFIRM) {
      this.popupMode = PopupMode.SUCCESS;
      this.popupTitle = 'Xóa thành công';
      this.popupMessage = 'Đồng hồ nước đã được xóa thành công!';
    } else if (this.popupMode === PopupMode.SUCCESS) {
      this.showPopup = false;
      this.removeMeter.emit(this.meter);
      this.close.emit();
    }
  }

  onPopupCancel(): void {
    this.showPopup = false;
  }

  onClose(): void {
    this.close.emit();
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
}
