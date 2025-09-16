import { Component, Input, Output, EventEmitter, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export enum PopupMode {
  CONFIRM = 'confirm',
  PASSWORD = 'password',
  SUCCESS = 'success',
  ERROR = 'error'
}

@Component({
  selector: 'lib-popup-confirm',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './popup-confirm.component.html',
  styleUrls: ['./popup-confirm.component.css']
})
export class PopupConfirmComponent implements OnChanges{
 @Input() isVisible: boolean = false;
  @Input() title: string = '';
  @Input() message: string = '';
  @Input() confirmText: string = '';
  @Input() cancelText: string = '';
  @Input() mode: PopupMode = PopupMode.CONFIRM;
  @Input() requiredPassword: string = '';

  @Output() confirm = new EventEmitter<any>();
  @Output() cancel = new EventEmitter<void>();
  @Output() passwordSubmit = new EventEmitter<string>();

  PopupMode = PopupMode;
  passwordValue: string = '';
  showPasswordError: boolean = false;

  onConfirm() {
    if (this.mode === PopupMode.PASSWORD) {
      if (this.passwordValue === this.requiredPassword) {
        this.showPasswordError = false;
        this.passwordSubmit.emit(this.passwordValue);
        this.confirm.emit({ password: this.passwordValue });
      } else {
        this.showPasswordError = true;
      }
    } else {
      this.confirm.emit();
    }
  }

  onCancel() {
    this.passwordValue = '';
    this.showPasswordError = false;
    this.cancel.emit();
  }

  ngOnChanges() {
    if (this.mode !== PopupMode.PASSWORD) {
      this.passwordValue = '';
      this.showPasswordError = false;
    }
  }
}
