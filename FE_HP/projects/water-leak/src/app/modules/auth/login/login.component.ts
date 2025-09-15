import { Component } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  showPassword = false;
   constructor(private router: Router) {}

  onLogin() {
    this.router.navigate(['/branches/predictive-model']);
  }
}
