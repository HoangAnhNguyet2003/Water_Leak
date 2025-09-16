import { NgModule } from '@angular/core';
import { MyLibComponent } from './my-lib.component';
import { PopupConfirmComponent } from './components/popup-confirm/popup-confirm.component';



@NgModule({
  declarations: [
    MyLibComponent
  ],
  imports: [
    PopupConfirmComponent
  ],
  exports: [
    MyLibComponent
  ]
})
export class MyLibModule { }
