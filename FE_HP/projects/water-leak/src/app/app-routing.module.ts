import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './modules/auth/login/login.component';
import { PredictiveModelComponent } from './modules/branches/predictive-model/components/predictive-model.component';
import { ManualModelComponent } from './modules/branches/manual-model/components/manual-model.component';
import { MeterManagementComponent } from './modules/branches/meter-management/components/meter-management.component';
import { DashboardComponent } from './modules/branches/dashboard/components/dashboard.component';
import { MainComponent } from './core/layout/main/main.component';
import { authGuard } from 'my-lib';

const routes: Routes = [
  { path: '', redirectTo: 'auth/login', pathMatch: 'full' },
  { path: 'auth/login', component: LoginComponent },

  // Branch Manager
  {
    path: '',
    component: MainComponent,
    canActivate: [authGuard],
    data: { role: 'branch_manager' },
    children: [
      { path: 'branches/dashboard', component: DashboardComponent },
      { path: 'branches/predictive-model', component: PredictiveModelComponent },
      { path: 'branches/manual-model', component: ManualModelComponent },
      { path: 'branches/manual-model/:meterId', component: ManualModelComponent }, // thêm meterId param
      { path: 'branches/meter-management', component: MeterManagementComponent },
      { path: '', redirectTo: 'branches/dashboard', pathMatch: 'full' }
    ]
  },

  // Company Manager
  {
    path: 'company',
    component: MainComponent,
    canActivate: [authGuard],
    data: { role: 'company_manager' },
    children: [
      {
        path: 'water-clock/chart/:id/:name',
        loadComponent: () =>
          import('./modules/company/water-clock/components/chart-view/chart-view.component')
            .then(m => m.ChartViewComponent)
      },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./modules/company/dashboard/components/main-component/main-component.component')
            .then(m => m.MainComponentComponent)
      },
      {
        path: 'water-clock',
        loadComponent: () =>
          import('./modules/company/water-clock/components/water-meter-info/water-meter-info.component')
            .then(m => m.WaterMeterInfoComponent)
      },
      {
        path: 'beak-history',
        loadComponent: () =>
          import('./modules/company/beak-history/components/break-history/break-history.component')
            .then(m => m.BreakHistoryComponent)
      },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
    ]
  },

  // Admin
  {
    path: 'admin',
    component: MainComponent,
    canActivate: [authGuard],
    data: { role: 'admin' },
    children: [
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./modules/admin/dashboard/components/dashboard-component/dashboard-component.component')
            .then(m => m.DashboardComponentComponent)
      },
      {
        path: 'user-manager',
        loadComponent: () =>
          import('./modules/admin/user-manager/components/um-components/um-components.component')
            .then(m => m.UmComponentsComponent)
      },
      {
        path: 'meter-manager',
        loadComponent: () =>
          import('./modules/admin/meter-manager/components/meter-main-component/meter-main-component.component')
            .then(m => m.MeterMainComponentComponent)
      },
      {
        path: 'logs',
        loadComponent: () =>
          import('./modules/admin/log/components/log-main/log-main.component')
            .then(m => m.LogMainComponent)
      },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
