import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent } from './modules/auth/login/login.component';
import { PredictiveModelComponent } from './modules/branches/predictive-model/predictive-model.component';
import { ManualModelComponent } from './modules/branches/manual-model/manual-model.component';
import { MeterManagementComponent } from './modules/branches/meter-management/meter-management.component';
import { DashboardComponentComponent } from './modules/admin/dashboard/components/dashboard-component/dashboard-component.component';
import { UmComponentsComponent } from './modules/admin/user-manager/components/um-components/um-components.component';
import { DropdownDetailsComponent } from './modules/admin/user-manager/components/dropdown-details/dropdown-details.component';
import { AddUserFormComponent } from './modules/admin/user-manager/components/add-user-form/add-user-form.component';
import { AddMeterFormComponent } from './modules/admin/meter-manager/components/add-meter-form/add-meter-form.component';
import { MeterDropdownDetailsComponent } from './modules/admin/meter-manager/components/meter-dropdown-details/meter-dropdown-details.component';
import { MeterMainComponentComponent } from './modules/admin/meter-manager/components/meter-main-component/meter-main-component.component';
import { PopupConfirmComponent } from 'projects/my-lib/src/lib/components';
import { LogMainComponent } from './modules/admin/log/components/log-main/log-main.component';
import { ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { AuthModule } from 'my-lib';
import { MainComponent } from "./core/layout/main/main.component";
import { SearchComponent } from './core/component/search/search.component';

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    PredictiveModelComponent,
    ManualModelComponent,
    
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    AuthModule,
    PopupConfirmComponent,
    UmComponentsComponent,
    DashboardComponentComponent,
    AddMeterFormComponent,
    MeterDropdownDetailsComponent,
    MeterMainComponentComponent,
    DropdownDetailsComponent,
    AddUserFormComponent,
    LogMainComponent,
    ReactiveFormsModule,
    MainComponent,
    SearchComponent,
    MeterManagementComponent,
],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }

