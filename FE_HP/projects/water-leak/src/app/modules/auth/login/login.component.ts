import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { AuthService } from 'my-lib'

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  private authService = inject(AuthService);
  private fb = inject(FormBuilder);
  private router = inject(Router);

  loginForm!: FormGroup;
  isLoading = false;
  showPassword = false;
  errorMessage = '';

  ngOnInit(): void {
    this.initForm();
  }

  private initForm(): void {
    this.loginForm = this.fb.group({
      username: ['', [Validators.required]],
      password: ['', [Validators.required]]
    });
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  onSubmit(): void {
    if (this.loginForm.valid) {
      this.isLoading = true;
      this.errorMessage = '';

      const loginRequest = {
        username: this.loginForm.value.username,
        password: this.loginForm.value.password
      };

      this.authService.login(loginRequest).subscribe({
        next: (response) => {
          console.log('🎉 Login success in component:', response);
          this.isLoading = false;
          const roleName = response?.roleName || 'unknown';
          console.log('👤 User role name:', roleName);
          this.navigateBasedOnRole(roleName);
        },
        error: (error: any) => {
          console.error('❌ Login error in component:', error);
          this.isLoading = false;
          this.errorMessage = error.message || 'Username hoặc mật khẩu không đúng. Vui lòng thử lại.';
        }
      });
    } else {
      this.markAllFormControlsTouched();
    }
  }

  private navigateBasedOnRole(roleName: string): void {
    switch (roleName.toLowerCase()) {
      case 'admin':
        window.location.href = 'http://localhost:4200/admin/dashboard';
        break;
      case 'branch_manager':
        window.location.href = 'http://localhost:4200/branches/predictive-model';
        break;
      default:
        this.router.navigate(['/dashboard']);
        break;
    }
  }

  private markAllFormControlsTouched(): void {
    Object.keys(this.loginForm.controls).forEach(key => {
      const control = this.loginForm.get(key);
      control?.markAsTouched();
    });
  }

  getErrorMessage(fieldName: string): string {
    const control = this.loginForm.get(fieldName);
    if (control?.errors && control.touched) {
      if (control.errors['required']) {
        return fieldName === 'username' ? 'Username là bắt buộc' : 'Mật khẩu là bắt buộc';
      }
    }
    return '';
  }
}
