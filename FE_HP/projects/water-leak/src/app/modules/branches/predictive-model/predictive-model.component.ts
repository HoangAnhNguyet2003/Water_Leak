import { Component, OnInit } from '@angular/core';
import { PredictService } from '../../../core/services/branches/predict.service';
@Component({
  selector: 'app-predictive-model',
  templateUrl: './predictive-model.component.html',
  styleUrls: ['./predictive-model.component.scss']
})
export class PredictiveModelComponent implements OnInit {
  data: any;

  constructor(private watchService: PredictService ) {}

  ngOnInit(): void {
    this.watchService.getPredictions().subscribe(res => {
      this.data = res;
    });
  }
}
