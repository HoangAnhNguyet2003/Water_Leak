import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class PredictService {

  constructor() { }

  getPredictions(): Observable<any> {
    // Giả lập dữ liệu JSON trả về từ Flask
    const data = {
      area: "Văn Đẩu 8",
      dates: ["04/03/2025","05/03/2025","06/03/2025","07/03/2025","08/03/2025","09/03/2025","10/03/2025"],
      models: [
        {
          name: "LSTM_minflow",
          results: ["Chưa có dữ liệu","Chưa có dữ liệu","Nghi ngờ thấp","Nghi ngờ cao","Nghi ngờ cao","Nghi ngờ cao","Nghi ngờ cao"]
        },
        {
          name: "LSTM_maxflow",
          results: ["Chưa có dữ liệu","Chưa có dữ liệu","Nghi ngờ cao","Nghi ngờ cao","Nghi ngờ cao","Nghi ngờ cao","Nghi ngờ cao"]
        },
        {
          name: "Isolation_minflow",
          results: ["Nghi ngờ thấp","Nghi ngờ thấp","Nghi ngờ thấp","Nghi ngờ thấp","Nghi ngờ thấp","Nghi ngờ thấp","Nghi ngờ thấp"]
        },
        {
          name: "Isolation_maxflow",
          results: ["Nghi ngờ thấp","Nghi ngờ thấp","Nghi ngờ thấp","Nghi ngờ thấp","Nghi ngờ thấp","Nghi ngờ thấp","Nghi ngờ thấp"]
        },
        {
          name: "Kết luận",
          results: ["Chưa xác định","Chưa xác định","Nghi ngờ thấp","Nghi ngờ trung bình","Nghi ngờ trung bình","Nghi ngờ trung bình","Nghi ngờ trung bình"]
        }
      ]
    };

    return of(data); // Trả về Observable như gọi API thật
  }
}
