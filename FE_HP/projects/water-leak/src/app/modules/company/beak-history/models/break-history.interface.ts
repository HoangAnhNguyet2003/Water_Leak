export interface BreakHistory {
  id: string;                     // _id trong DB
  meterId?: string;               // id đồng hồ (có thể null)
  meterName?: string;             // tên đồng hồ
  recordedTime?: string | Date;          // thời gian ghi nhận
  repairTime?: string | Date;            // thời gian sửa chữa
  leakReason?: string;            // nguyên nhân rò rỉ
  leakFix?: string;               // cách khắc phục
  replacementLocation?: string;    // vị trí thay thế
  replacementType?: string;       // loại thay thế
  selected?: boolean;             // FE dùng để check
  expanded?: boolean;             // FE dùng để toggle hiển thị
}

export interface BreakHistoryFilter {
  searchTerm: string;  
}