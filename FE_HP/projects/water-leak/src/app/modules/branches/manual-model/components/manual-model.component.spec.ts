import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ManualModelComponent } from './manual-model.component';

describe('ManualModelComponent', () => {
  let component: ManualModelComponent;
  let fixture: ComponentFixture<ManualModelComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ManualModelComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ManualModelComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
