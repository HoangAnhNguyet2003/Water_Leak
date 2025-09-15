import { Component, OnInit } from '@angular/core';
import { MeterService } from '../../../core/services/branches/meter.service';

@Component({
  selector: 'app-meter-management',
  templateUrl: './meter-management.component.html',
  styleUrls: ['./meter-management.component.scss']
})
export class MeterManagementComponent implements OnInit {
  meters: any[] = [];

  constructor(private meterService: MeterService) {}

  ngOnInit(): void {
    this.meterService.getMeters().subscribe(res => {
      this.meters = res;
    });
  }
}
