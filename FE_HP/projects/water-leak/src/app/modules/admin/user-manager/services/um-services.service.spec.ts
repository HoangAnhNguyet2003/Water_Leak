import { TestBed } from '@angular/core/testing';

import { UmServicesService } from './um-services.service';

describe('UmServicesService', () => {
  let service: UmServicesService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(UmServicesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
