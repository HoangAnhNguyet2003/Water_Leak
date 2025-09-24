import { Component, signal, inject, OnInit, computed, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { UserData, UserRole } from '../../models';
import { UmServicesService } from '../../services/um-services.service';
import { catchError } from 'rxjs/operators';
import { SearchFilterUtils } from 'projects/my-lib/src/lib/utils/search-filter.utils';
import { DropdownDetailsComponent } from '../dropdown-details/dropdown-details.component';
import { AddUserFormComponent } from '../add-user-form/add-user-form.component';

@Component({
  selector: 'app-um-components',
  standalone: true,
  imports: [CommonModule, FormsModule, DropdownDetailsComponent, AddUserFormComponent],
  templateUrl: './um-components.component.html',
  styleUrls: ['./um-components.component.scss']
})
export class UmComponentsComponent {
  userDataService = inject(UmServicesService);
  allUserData = signal<UserData[]>([]);
  searchTerm = signal<string>('');
  selectedRole = signal<string>('');
  activeDropdown = signal<number | null>(null);
  showAddUserForm = signal<boolean>(false);

  filteredUserData = computed(() => {
    const users = this.allUserData();
    const search = this.searchTerm();
    const roleFilter = this.selectedRole();

    return SearchFilterUtils.universalFilter(
      users,
      search,
      ['username'],
      roleFilter ? [{ field: 'roleName', value: roleFilter }] : []
    );
  });

  ngOnInit(): void {
    this.loadUserData();
  }

  loadUserData(): void {
    this.userDataService.getAllUsers().pipe(
      catchError((err) => {
        console.error('Error fetching users from API, falling back to mock', err);
        throw err;
      })
    ).subscribe((users: UserData[]) => {
      this.allUserData.set(users);
    });
  }

  onSearchChange(searchValue: string): void {
    this.searchTerm.set(searchValue);
  }

  onRoleFilterChange(role: string): void {
    this.selectedRole.set(role);
  }

  clearFilters(): void {
    this.searchTerm.set('');
    this.selectedRole.set('');
  }

  getRoleLabel(role: UserRole | string): string {
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
    return isActive ? 'Kích hoạt' : 'Vô hiệu hóa';
  }

  editUser(user: UserData): void {
    console.log('Edit user:', user);
    // TODO: Implement edit user functionality
  }

  onChangeInformation(user: UserData): void {
    console.log('Change information for user:', user);
    // Don't close dropdown immediately, let the child component handle the edit mode
    // this.closeDropdown();
    // TODO: Implement change information functionality
  }

  onRemoveUser(user: UserData, dropdownComponent: any): void {
    console.log('onDeleteUser called for user:', user.username);
    const uid = String(user.id);
    console.log('[PARENT] onRemoveUser called', user.id, 'dropdownComponentExists=', !!dropdownComponent);

        this.userDataService.deleteUser(uid).subscribe({
      next: (result) => {
        if (dropdownComponent?.showDeleteResult) {
          dropdownComponent.showDeleteResult(result.success, result.error);
        }
        if (result.success) {
          setTimeout(() => {
            this.allUserData.set(this.allUserData().filter(u => String(u.id) !== uid));
          }, 500);
        }
      },
      error: (err) => {
        if (dropdownComponent?.showDeleteResult) {
          dropdownComponent.showDeleteResult(false, err);
        }
      }
    });
  }

  showAddUserPopup(): void {
    this.showAddUserForm.set(true);
  }

  onUserAdded(newUser: UserData): void {
    // Add new user to the list
    const currentUsers = this.allUserData();
    this.allUserData.set([...currentUsers, newUser]);
    this.showAddUserForm.set(false);
    console.log('New user added:', newUser);
  }

  onAddUserCancel(): void {
    this.showAddUserForm.set(false);
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
      if (!target.closest('.action-dropdown') && !target.closest('.dropdown-details-inline')) {
        this.activeDropdown.set(null);
      }
    }
  }
}
