import { TestBed } from '@angular/core/testing';

import { MeterManagerService } from './meter-manager.service';

describe('MeterManagerService', () => {
  let service: MeterManagerService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(MeterManagerService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
