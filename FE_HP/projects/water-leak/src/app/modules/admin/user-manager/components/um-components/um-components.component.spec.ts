import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UmComponentsComponent } from './um-components.component';

describe('UmComponentsComponent', () => {
  let component: UmComponentsComponent;
  let fixture: ComponentFixture<UmComponentsComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [UmComponentsComponent]
    });
    fixture = TestBed.createComponent(UmComponentsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
