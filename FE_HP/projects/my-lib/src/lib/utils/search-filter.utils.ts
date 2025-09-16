// Shared interfaces for filtering and searching
export interface FilterableItem {
  id: number | string;
  [key: string]: any;
}

export interface FilterConfig {
  searchFields: string[];
  filterField?: string;
  filterOptions?: Array<{ value: string; label: string }>;
}

export class SearchFilterUtils {

  static search<T extends FilterableItem>(
    items: T[],
    searchTerm: string,
    searchFields: string[] = ['name']
  ): T[] {
    if (!searchTerm) return items;

    const term = searchTerm.toLowerCase();
    return items.filter(item => {
      return searchFields.some(field => {
        const fieldValue = item[field];
        return fieldValue && fieldValue.toString().toLowerCase().includes(term);
      });
    });
  }

  static filter<T extends FilterableItem>(
    items: T[],
    filterValue: string,
    filterField: string
  ): T[] {
    if (!filterValue) return items;

    return items.filter(item => {
      const fieldValue = item[filterField];
      return fieldValue && fieldValue.toString() === filterValue;
    });
  }

  static searchAndFilter<T extends FilterableItem>(
    items: T[],
    searchTerm: string,
    searchFields: string[] = ['name']
  ): T[] {
    return this.search(items, searchTerm, searchFields);
  }

  static filterByConditions<T extends FilterableItem>(
    items: T[],
    conditions: { field: string; value: any }[]
  ): T[] {
    return items.filter(item => {
      return conditions.every(condition => {
        if (!condition.value) return true;
        const fieldValue = item[condition.field];
        return fieldValue && fieldValue.toString() === condition.value.toString();
      });
    });
  }

  static universalFilter<T extends FilterableItem>(
    items: T[],
    searchTerm?: string,
    searchFields?: string[],
    filterConditions?: { field: string; value: any }[]
  ): T[] {
    let result = items;

    if (searchTerm && searchFields) {
      result = this.search(result, searchTerm, searchFields);
    }

    if (filterConditions) {
      result = this.filterByConditions(result, filterConditions);
    }

    return result;
  }

  static filterByDateRange<T extends FilterableItem>(
    items: T[],
    dateField: string,
    startDate?: string,
    endDate?: string
  ): T[] {
    if (!startDate && !endDate) return items;

    return items.filter(item => {
      const itemDate = new Date(item[dateField]);
      const start = startDate ? new Date(startDate) : new Date('1900-01-01');
      const end = endDate ? new Date(endDate) : new Date('2100-12-31');
      return itemDate >= start && itemDate <= end;
    });
  }
}

export class DateUtils {

  static formatDate(date: Date | string): string {
    const d = new Date(date);
    const day = d.getDate().toString().padStart(2, '0');
    const month = (d.getMonth() + 1).toString().padStart(2, '0');
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  }

  static formatDateTime(date: Date | string): string {
    const d = new Date(date);
    const day = d.getDate().toString().padStart(2, '0');
    const month = (d.getMonth() + 1).toString().padStart(2, '0');
    const year = d.getFullYear();
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    return `${day}/${month}/${year} ${hours}:${minutes}`;
  }

  static isValidDate(date: any): boolean {
    return date instanceof Date && !isNaN(date.getTime());
  }
}
