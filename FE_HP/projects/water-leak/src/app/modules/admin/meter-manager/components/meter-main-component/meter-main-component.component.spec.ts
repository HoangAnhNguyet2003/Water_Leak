import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MeterMainComponentComponent } from './meter-main-component.component';

describe('MeterMainComponentComponent', () => {
  let component: MeterMainComponentComponent;
  let fixture: ComponentFixture<MeterMainComponentComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [MeterMainComponentComponent]
    });
    fixture = TestBed.createComponent(MeterMainComponentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
