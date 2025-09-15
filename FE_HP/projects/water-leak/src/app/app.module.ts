import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent } from './modules/auth/login/login.component';
import { PredictiveModelComponent } from './modules/branches/predictive-model/predictive-model.component';
import { ManualModelComponent } from './modules/branches/manual-model/manual-model.component';
import { MeterManagementComponent } from './modules/branches/meter-management/meter-management.component';
@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    PredictiveModelComponent,
    ManualModelComponent,
    MeterManagementComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
