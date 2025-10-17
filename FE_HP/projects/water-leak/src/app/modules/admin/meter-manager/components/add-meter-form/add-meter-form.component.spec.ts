import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AddMeterFormComponent } from './add-meter-form.component';

describe('AddMeterFormComponent', () => {
  let component: AddMeterFormComponent;
  let fixture: ComponentFixture<AddMeterFormComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [AddMeterFormComponent]
    });
    fixture = TestBed.createComponent(AddMeterFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
