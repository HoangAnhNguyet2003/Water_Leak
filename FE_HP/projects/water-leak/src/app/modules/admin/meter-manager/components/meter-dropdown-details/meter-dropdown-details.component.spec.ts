import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MeterDropdownDetailsComponent } from './meter-dropdown-details.component';

describe('MeterDropdownDetailsComponent', () => {
  let component: MeterDropdownDetailsComponent;
  let fixture: ComponentFixture<MeterDropdownDetailsComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [MeterDropdownDetailsComponent]
    });
    fixture = TestBed.createComponent(MeterDropdownDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
