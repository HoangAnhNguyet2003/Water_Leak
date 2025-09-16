import { Component, signal, inject, OnInit, computed } from '@angular/core';
import { LogMetaData, LogType } from '../../models';
import { LogServiceService } from '../../services/log-service.service';
import { catchError } from 'rxjs';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DateUtils, SearchFilterUtils } from 'projects/my-lib/src/lib/utils/search-filter.utils';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

@Component({
  selector: 'app-log-main',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './log-main.component.html',
  styleUrls: ['./log-main.component.scss']
})
export class LogMainComponent {
  LogService = inject(LogServiceService);
  LogData = signal<LogMetaData[]>([]);

  selectedLogType = signal<number | null>(null);
  startDate = signal<string>('');
  endDate = signal<string>('');

  LogType = LogType;

  filteredLogData = computed(() => {
    let data = this.LogData();

    const filterConditions: { field: string; value: any }[] = [];

    if (this.selectedLogType() !== null) {
      filterConditions.push({ field: 'log_type', value: this.selectedLogType() });
    }

    data = SearchFilterUtils.filterByConditions(data, filterConditions);

    data = SearchFilterUtils.filterByDateRange(
      data,
      'created_time',
      this.startDate(),
      this.endDate()
    );

    return data;
  });

  // ngOnInit(): void {
  //   this.LogService.getMockLogData().pipe(
  //     catchError((err) => {
  //       console.log(err);
  //       throw err;
  //     })
  //   ).subscribe((data) => {
  //     this.LogData.set(data);
  //   });
  // }

  onLogTypeChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    this.selectedLogType.set(target.value ? parseInt(target.value) : null);
  }

  onStartDateChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.startDate.set(target.value);
  }

  onEndDateChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.endDate.set(target.value);
  }

  getLogTypeDisplay(logType: number): string {
    switch (logType) {
      case LogType.WARNING:
        return 'Warning';
      case LogType.ERROR:
        return 'Error';
      case LogType.INFO:
        return 'Info';
      default:
        return 'Unknown';
    }
  }

  getLogTypeClass(logType: number): string {
    switch (logType) {
      case LogType.WARNING:
        return 'log-warning';
      case LogType.ERROR:
        return 'log-error';
      case LogType.INFO:
        return 'log-info';
      default:
        return 'log-unknown';
    }
  }

  formatDateTime(date: Date): string {
    return DateUtils.formatDateTime(date);
  }

  exportToPDF(): void {
    const filteredData = this.filteredLogData();

    const doc = new jsPDF();

    doc.setFontSize(20);
    doc.setFont('helvetica', 'bold');
    doc.text('Log Report', 105, 20, { align: 'center' });

    doc.setFontSize(12);
    doc.setFont('helvetica', 'normal');
    const exportDate = new Date().toLocaleString();
    doc.text(`Export Date: ${exportDate}`, 20, 35);
    doc.text(`Total Records: ${filteredData.length}`, 20, 45);

    const tableColumns = ['ID', 'Type', 'Created Time', 'Message'];
    const tableRows = filteredData.map(log => [
      log.id.toString(),
      this.getLogTypeDisplay(log.log_type),
      this.formatDateTime(log.created_time),
      log.message
    ]);

    autoTable(doc, {
      head: [tableColumns],
      body: tableRows,
      startY: 55,
      styles: {
        fontSize: 10,
        cellPadding: 5,
      },
      headStyles: {
        fillColor: [245, 245, 245],
        textColor: [0, 0, 0],
        fontStyle: 'bold',
      },
      columnStyles: {
        0: { cellWidth: 20 }, // ID column
        1: { cellWidth: 25 }, // Type column
        2: { cellWidth: 45 }, // Created Time column
        3: { cellWidth: 'auto' }, // Message column
      },
      didParseCell: (data) => {
        if (data.section === 'body' && data.column.index === 1) {
          const logType = data.cell.text[0];
          if (logType === 'Error') {
            data.cell.styles.textColor = [220, 53, 69];
          } else if (logType === 'Warning') {
            data.cell.styles.textColor = [255, 193, 7];
          } else if (logType === 'Info') {
            data.cell.styles.textColor = [40, 167, 69];
          }
        }
      },
      margin: { top: 55, left: 20, right: 20 },
    });

    const fileName = `log-report-${new Date().toISOString().split('T')[0]}.pdf`;
    doc.save(fileName);
  }

  clearFilters(): void {
    this.selectedLogType.set(null);
    this.startDate.set('');
    this.endDate.set('');
  }
}
