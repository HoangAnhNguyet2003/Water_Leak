import { Component, Output, EventEmitter, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WaterMeter, WaterMeterStatus } from '../../models';
import { PopupConfirmComponent, PopupMode } from 'projects/my-lib/src/lib/components';
import { MeterManagerService } from '../../services/meter-manager.service';
import { UmServicesService } from '../../../user-manager/services/um-services.service';
import { Branch } from '../../../user-manager/models';

@Component({
  selector: 'app-add-meter-form',
  standalone: true,
  imports: [CommonModule, FormsModule, PopupConfirmComponent],
  templateUrl: './add-meter-form.component.html',
  styleUrls: ['./add-meter-form.component.scss']
})
export class AddMeterFormComponent {
  @Input() isVisible = false;
  @Output() meterAdded = new EventEmitter<WaterMeter>();
  @Output() cancel = new EventEmitter<void>();

  showConfirmPopup = false;
  showSuccessPopup = false;

  WaterMeterStatus = WaterMeterStatus;
  PopupMode = PopupMode;

  newMeter: WaterMeter = {
    id: 0,
    name: '',
    branchName: '',
    status: WaterMeterStatus.NORMAL,
    installationDate: new Date()
  };

  selectedBranchId = '';
  installDate = '';

  availableBranches: Branch[] = [];

  private meterService = inject(MeterManagerService);
  private userService = inject(UmServicesService);

  constructor() {
    this.userService.getAllBranches().subscribe(b => {
      this.availableBranches = (b || []).map((x: any) => ({
        id: x._id || x.id || String(x._id || x.id || ''),
        name: x.name || '',
        address: x.address || ''
      }));
    });
  }

  onSubmit(): void {
    this.showConfirmPopup = true;
  }

  onConfirmAddMeter(): void {
    this.showConfirmPopup = false;

    const payload = {
      branch_name: this.getSelectedBranch()?.name || null,
      meter_name: this.newMeter.name,
      installation_time: this.installDate ? new Date(this.installDate).toISOString() : null
    };

    this.meterService.addMeter(payload).subscribe(created => {
      if (created) {
        this.meterAdded.emit(created);
        this.showSuccessPopup = true;
      } else {
        console.error('Failed to create meter on server');
        this.newMeter.id = Date.now();
        this.newMeter.installationDate = this.installDate ? new Date(this.installDate) : new Date();
        this.meterAdded.emit({ ...this.newMeter });
        this.showSuccessPopup = true;
      }
    });
  }

  onCancelConfirm(): void {
    this.showConfirmPopup = false;
  }

  onCloseSuccess(): void {
    this.showSuccessPopup = false;
    this.resetForm();
    this.cancel.emit();
  }

  onCancel(): void {
    this.resetForm();
    this.cancel.emit();
  }

  resetForm(): void {
    this.newMeter = {
      id: 0,
      name: '',
      branchName: '',
      status: WaterMeterStatus.NORMAL,
      installationDate: new Date()
    };
    this.selectedBranchId = '';
    this.installDate = '';
    this.showConfirmPopup = false;
    this.showSuccessPopup = false;
  }

  getSelectedBranch(): Branch | undefined {
    return this.availableBranches.find(branch => branch.id === this.selectedBranchId);
  }
}
