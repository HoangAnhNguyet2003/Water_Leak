export type LogMetaData = {
  id: string,
  source: string,
  log_type: number,
  created_time: string | Date,
  message: string
}

export enum LogType {
  INFO = 1,
  WARNING = 2,
  ERROR = 3
}
