import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './modules/auth/login/login.component';
import { PredictiveModelComponent } from './modules/branches/predictive-model/predictive-model.component';
import { ManualModelComponent } from './modules/branches/manual-model/manual-model.component';
import { MeterManagementComponent } from './modules/branches/meter-management/meter-management.component';
import { MainComponent } from './core/layout/main/main.component';
import { BreakHistoryComponent } from './modules/company/beak-history/components/break-history/break-history.component';
import { MainComponentComponent } from './modules/company/dashboard/components/main-component/main-component.component';
import { WaterMeterInfoComponent } from './modules/company/water-clock/components/water-meter-info/water-meter-info.component';

const routes: Routes = [
  { path: '', redirectTo: 'auth/login', pathMatch: 'full' }, 
  { path: 'auth/login', component: LoginComponent }, 
  {
    path: '',
    component: MainComponent,
    children: [
      { path: 'branches/predictive-model', component: PredictiveModelComponent },
      { path: 'branches/manual-model', component: ManualModelComponent },
      { path: 'branches/meter-management', component: MeterManagementComponent },
      { path: 'company/beak-history', component: BreakHistoryComponent},
      { path: 'company/dashboard', component: MainComponentComponent},
      { path: 'company/water-clock', component: WaterMeterInfoComponent}
    ]
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }