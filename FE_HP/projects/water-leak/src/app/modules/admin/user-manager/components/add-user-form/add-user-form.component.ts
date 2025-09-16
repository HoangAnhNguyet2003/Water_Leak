import { Component, Output, EventEmitter, Input, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { UserData, UserRole } from '../../models';
import { PopupConfirmComponent, PopupMode } from 'projects/my-lib/src/lib/components';
import { WaterMeter } from '../../../meter-manager/models';
import { Observable, of } from 'rxjs';
import { catchError, finalize, take } from 'rxjs/operators';
import { MeterManagerService } from '../../../meter-manager/services/meter-manager.service';
import { UmServicesService } from '../../services/um-services.service';
import { Branch } from '../../models';

@Component({
  selector: 'app-add-user-form',
  standalone: true,
  imports: [CommonModule, FormsModule, PopupConfirmComponent],
  templateUrl: './add-user-form.component.html',
  styleUrls: ['./add-user-form.component.scss']
})
export class AddUserFormComponent {
  @Input() isVisible = false;
  @Output() cancel = new EventEmitter<void>();

  private userDataService = inject(UmServicesService);
  private meterService = inject(MeterManagerService);

  availableWaterMeters$: Observable<WaterMeter[]> = new Observable();
  branches$: Observable<Branch[]> = new Observable();

  // Popup states
  showConfirmPopup = false;
  showSuccessPopup = false;
  showErrorPopup = false;
  errorMessage = '';

  // Form data
  newUser: UserData = this.getEmptyUser();
  confirmPassword = '';
  showPassword = false;
  showConfirmPassword = false;

  UserRole = UserRole;
  PopupMode = PopupMode;

  submitting = false;

  ngOnInit(): void {
    this.availableWaterMeters$ = this.meterService.getMeterData(false).pipe(
      catchError(err => {
        console.error('Failed to load meters:', err);
        return of([] as WaterMeter[]);
      })
    );
    this.branches$ = this.userDataService.getAllBranches().pipe(
      catchError(err => of([]))
    );
  }

  onRoleChange(role: UserRole | string) {
    this.newUser.roleName = role as UserRole;
    if (this.newUser.roleName === this.UserRole.Company) {
      this.availableWaterMeters$.pipe(take(1)).subscribe(meters => {
        this.newUser.managedWaterMeter = meters ? [...meters] : [];
      });
      this.newUser.branchId = null as any;
    } else if (this.newUser.roleName === this.UserRole.Admin) {
      this.newUser.managedWaterMeter = [];
      this.newUser.branchId = null as any;
    }
  }


  onSubmit(): void {
    if (!this.isPasswordValid()) return;
    this.showConfirmPopup = true;
  }

  onConfirmAddUser(): void {
    this.showConfirmPopup = false;
    this.submitting = true;

    const payload: any = {
      user_name: this.newUser.username,
      password_user: this.newUser.password,
      role_name: this.newUser.roleName,
      branch_id: this.newUser.branchId || null,
      is_active: this.newUser.isActive,
      managed_water_meter: this.newUser.managedWaterMeter?.map(meter => meter.id), // chỉ lấy id
      last_login: new Date().toISOString().split('T')[0],
    };

    console.log('Creating user payload:', payload);
    this.userDataService.createUser(payload)
      .pipe(finalize(() => this.submitting = false))
      .subscribe(res => {
        if (res.success) {
          this.userDataService.getAllUsers(true);
          this.showSuccessPopup = true;
        } else {
          console.error('Failed to create user:', res.error);
          this.errorMessage = res.error?.message || 'Có lỗi xảy ra';
          this.showErrorPopup = true;
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

  onCloseError(): void {
    this.showErrorPopup = false;
  }

  onCancel(): void {
    this.resetForm();
    this.cancel.emit();
  }

  resetForm(): void {
    this.newUser = this.getEmptyUser();
    this.confirmPassword = '';
    this.showPassword = false;
    this.showConfirmPassword = false;
    this.showConfirmPopup = false;
    this.showSuccessPopup = false;
    this.showErrorPopup = false;
    this.errorMessage = '';
  }

  isPasswordValid(): boolean {
    return !!this.newUser.password && !!this.confirmPassword && this.newUser.password === this.confirmPassword;
  }

  togglePasswordVisibility(event?: Event): void {
    event?.stopPropagation();
    this.showPassword = !this.showPassword;
  }

  toggleConfirmPasswordVisibility(event?: Event): void {
    event?.stopPropagation();
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  isWaterMeterSelected(meterId: string | number): boolean {
    return this.newUser.managedWaterMeter?.some(m => String(m.id) === String(meterId)) || false;
  }

  toggleWaterMeter(waterMeter: WaterMeter): void {
    if (!this.newUser.managedWaterMeter) this.newUser.managedWaterMeter = [];
    const selected = this.isWaterMeterSelected(waterMeter.id);
    this.newUser.managedWaterMeter = selected
      ? this.newUser.managedWaterMeter.filter(m => String(m.id) !== String(waterMeter.id))
      : [...this.newUser.managedWaterMeter, waterMeter];
  }

  onMeterClick(waterMeter: WaterMeter, event?: Event): void {
    event?.stopPropagation();
    if (this.newUser.roleName === this.UserRole.Admin) {
      return;
    }
    this.toggleWaterMeter(waterMeter);
  }

  private getEmptyUser(): UserData {
    return {
      id: '',
      username: '',
      roleName: UserRole.Branch,
      isActive: true,
      lastLogin: null,
      password: '',
      managedWaterMeter: []
    };
  }
}
