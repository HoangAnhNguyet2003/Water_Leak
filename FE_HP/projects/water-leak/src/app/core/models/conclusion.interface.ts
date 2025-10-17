export interface ConclusionResult {
  text: string;
  color: string;
}

export interface CachedPrediction {
  meterId: string;
  predictions: any[];
  lastUpdated: Date;
}

export interface CachedConclusion {
  meterId: string;
  dateStr: string;
  conclusion: ConclusionResult;
  lastUpdated: Date;
}
