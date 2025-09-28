import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MeterManagementComponent } from './meter-management.component';

describe('MeterManagementComponent', () => {
  let component: MeterManagementComponent;
  let fixture: ComponentFixture<MeterManagementComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ MeterManagementComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MeterManagementComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
