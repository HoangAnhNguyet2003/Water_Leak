export type LogMetaData = {
  id: number,
  log_type: number,
  created_time: Date,
  message: string
}

export enum LogType {
  WARNING = 1,
  ERROR = 2,
  INFO = 3
}
