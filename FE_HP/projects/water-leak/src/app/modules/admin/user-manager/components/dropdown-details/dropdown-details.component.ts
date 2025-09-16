import { Component, Input, Output, EventEmitter, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { UserData, UserRole } from '../../models';
import { WaterMeter, WaterMeterStatus } from '../../../meter-manager/models';
import { PopupConfirmComponent, PopupMode } from 'projects/my-lib/src/lib/components';
import { catchError, take, map } from 'rxjs/operators';
import { Observable, of } from 'rxjs';
import { UmServicesService } from '../../services/um-services.service';
import { MeterManagerService } from '../../../meter-manager/services/meter-manager.service';
import { Branch } from '../../models';

@Component({
  selector: 'app-dropdown-details',
  standalone: true,
  imports: [CommonModule, FormsModule, PopupConfirmComponent],
  templateUrl: './dropdown-details.component.html',
  styleUrls: ['./dropdown-details.component.scss']
})
export class DropdownDetailsComponent {
  @Input() user!: UserData;
  @Input() isVisible = false;
  @Output() changeInfo = new EventEmitter<UserData>();
  @Output() removeUser = new EventEmitter<UserData>();
  @Output() close = new EventEmitter<void>();
  @Output() deleteUser = new EventEmitter<UserData>();

  isEditMode = false;
  editedUser!: UserData;
  confirmPassword = '';
  showPassword = false;
  showConfirmPassword = false;

  showPopup = false;
  popupMode = PopupMode.CONFIRM;
  popupTitle = '';
  popupMessage = '';
  currentAction = '';

  PopupMode = PopupMode;
  UserRole = UserRole;

  private meterService = inject(MeterManagerService);
  private userService = inject(UmServicesService);
  availableWaterMeters$: Observable<WaterMeter[]> = new Observable();
  branches$: Observable<Branch[]> = new Observable();

  ngOnInit() {
    this.availableWaterMeters$ = this.meterService.getMeterData(false).pipe(
          catchError(err => {
            console.error('Failed to load meters:', err);
            return of([] as WaterMeter[]);
          })
        );
    this.branches$ = this.userService.getAllBranches().pipe(
      map((items: any[]) => (items || []).map((x: any) => ({ id: x._id || x.id, name: x.name, address: x.address || '' }))),
      catchError(err => {
        console.error('Failed to load branches:', err);
        return of([] as any[]);
      })
    );
    console.log('DropdownDetailsComponent initialized');
    console.log('User data:', this.user);
    console.log('isVisible:', this.isVisible);
    this.resetEditedUser();
  }

  resetEditedUser() {
    if (!this.user) {
      this.editedUser = {
        id: '' as any,
        username: '',
        password: '',
        roleName: UserRole.Branch,
        isActive: true,
        lastLogin: null,
        managedWaterMeter: []
      } as UserData;
      this.confirmPassword = '';
      return;
    }

    this.editedUser = {
      ...this.user,
      roleName: (this.user as any).roleName || (this.user as any).role || UserRole.Branch,
      isActive: (this.user as any).isActive !== undefined ? (this.user as any).isActive : true,
      lastLogin: (this.user as any).lastLogin || null,
  branchId: (this.user as any).branchId ?? (this.user as any).branch_id ?? '',
      managedWaterMeter: this.user.managedWaterMeter ? [...this.user.managedWaterMeter] : []
    } as UserData;

    this.confirmPassword = '';
  }

  onChangeInformation(): void {
    console.log('Change Information button clicked!');
    console.log('Current isEditMode:', this.isEditMode);
    this.isEditMode = true;
    console.log('New isEditMode:', this.isEditMode);
    this.resetEditedUser();
  }

  onRoleChange(role: UserRole | string) {
    this.editedUser.roleName = role as UserRole;
    // If Company -> select all meters and clear branch (company sees all)
    if (this.editedUser.roleName === this.UserRole.Company) {
      this.availableWaterMeters$.pipe(take(1)).subscribe(meters => {
        this.editedUser.managedWaterMeter = meters ? [...meters] : [];
      });
      this.editedUser.branchId = null as any;
    } else if (this.editedUser.roleName === this.UserRole.Admin) {
      // Admin -> cannot manage any meters and no branch
      this.editedUser.managedWaterMeter = [];
      this.editedUser.branchId = null as any;
    }
  }

  onSaveChanges(): void {
    if (this.editedUser.password && this.editedUser.password !== this.confirmPassword) {
      alert('Mật khẩu và xác nhận mật khẩu không khớp!');
      return;
    }

    this.currentAction = 'save';
    this.popupMode = PopupMode.CONFIRM;
    this.popupTitle = 'Xác nhận lưu thay đổi';
    this.popupMessage = 'Bạn có chắc chắn muốn lưu những thay đổi này không?';
    this.showPopup = true;
  }

  onRemoveUser(): void {
    this.currentAction = 'delete';
    this.popupMode = PopupMode.CONFIRM;
    this.popupTitle = 'Xác nhận xóa người dùng';
    this.popupMessage = 'Bạn có chắc chắn muốn xóa người dùng này không? Hành động này không thể hoàn tác.';
    this.showPopup = true;
  }

  onPopupConfirm(data?: any): void {
    console.log('[DD] onPopupConfirm', { popupMode: this.popupMode, currentAction: this.currentAction });

    if (this.popupMode === PopupMode.CONFIRM) {
      if (this.currentAction === 'delete') {
        this.removeUser.emit(this.user);


        // this.showPopup = false;
        // this.currentAction = '';
        return;
      }

      if (this.currentAction === 'save') {
        const payload: any = {
          user_name: this.editedUser.username,
          role_name: this.editedUser.roleName,
          is_active: this.editedUser.isActive,
          branch_id: (this.editedUser.branchId === '' || this.editedUser.branchId == null) ? null : this.editedUser.branchId,
          managed_water_meter: this.editedUser.managedWaterMeter?.map((m: any) => m.id) || [],
        };
        if (this.editedUser.password) payload.password_user = this.editedUser.password;
        this.userService.updateUser(this.editedUser.id, payload).subscribe((res: any) => {
          if (res.success) {
            this.popupMode = PopupMode.SUCCESS;
            this.popupTitle = 'Cập nhật thành công';
            this.popupMessage = 'Thông tin người dùng đã được cập nhật thành công!';
          } else {
            this.popupMode = PopupMode.ERROR;
            this.popupTitle = 'Cập nhật thất bại';
            this.popupMessage = res.error?.message || 'Không thể cập nhật người dùng.';
          }
        });
        return;
      }
    }

    if (this.popupMode === PopupMode.SUCCESS || this.popupMode === PopupMode.ERROR) {
      this.showPopup = false;

      if (this.currentAction === 'save') {
        this.changeInfo.emit(this.editedUser);
        this.isEditMode = false;
      }

      this.currentAction = '';
      this.close.emit();
    }
  }


  showDeleteResult(success: boolean, info?: any) {
    this.showPopup = true;
    this.currentAction = 'delete';

    if (success) {
      this.popupMode = PopupMode.SUCCESS;
      this.popupTitle = 'Xóa thành công';
      this.popupMessage = 'Người dùng đã được xóa thành công.';
    } else {
      this.popupMode = PopupMode.ERROR;
      this.popupTitle = 'Xóa thất bại';
      this.popupMessage = info?.status === 403
        ? 'Bạn không thể xóa user Admin!'
        : 'Không thể xóa người dùng.';
    }
  }

  onPopupCancel(): void {
    this.showPopup = false;
    this.currentAction = '';
  }


  isPasswordValid(): boolean {
    if (!this.editedUser.password || !this.confirmPassword) {
      return true; // Allow empty passwords for now
    }
    return this.editedUser.password === this.confirmPassword;
  }

  togglePasswordVisibility(event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.showPassword = !this.showPassword;
  }

  toggleConfirmPasswordVisibility(event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  onCancelEdit(): void {
    this.isEditMode = false;
    this.resetEditedUser();
  }

  onClose(): void {
    this.close.emit();
  }

  isWaterMeterSelected(waterId: string | number): boolean {
    return this.editedUser.managedWaterMeter?.some(meter => meter.id === waterId) || false;
  }

  toggleWaterMeter(waterMeter: WaterMeter): void {
    if (this.editedUser.roleName === this.UserRole.Admin) {
      return;
    }

    if (!this.editedUser.managedWaterMeter) {
      this.editedUser.managedWaterMeter = [];
    }

    const isSelected = this.isWaterMeterSelected(waterMeter.id);
    if (isSelected) {
      this.editedUser.managedWaterMeter = this.editedUser.managedWaterMeter.filter(meter => meter.id !== waterMeter.id);
    } else {
      this.editedUser.managedWaterMeter.push(waterMeter);
    }
  }

  onMeterClick(waterMeter: WaterMeter, event?: Event): void {
    event?.stopPropagation();
    if (this.editedUser.roleName === this.UserRole.Admin) return;
    this.toggleWaterMeter(waterMeter);
  }

  getRoleLabel(role: string): string {
    switch (role) {
      case UserRole.Admin:
        return 'Administrator';
      case UserRole.Company:
        return 'Tổng công ty';
      case UserRole.Branch:
        return 'Chi nhánh';
      default:
        return 'Unknown';
    }
  }

  getStatusLabel(isActive: boolean): string {
    return isActive ? 'Hoạt động' : 'Không hoạt động';
  }
}
