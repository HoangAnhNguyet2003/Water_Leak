import { Injectable } from '@angular/core';
import { Observable, BehaviorSubject } from 'rxjs';
import { PredictiveModelService } from '../../../modules/branches/predictive-model/services/predictive-model.service';
import { CachedConclusion, CachedPrediction, ConclusionResult } from '../../models/conclusion.interface';


@Injectable({
  providedIn: 'root'
})
export class ConclusionService {

  private lstmAutoencoderCache$ = new BehaviorSubject<CachedPrediction[]>([]);

  private lstmPredictionsCache$ = new BehaviorSubject<CachedPrediction[]>([]);

  private conclusionsCache$ = new BehaviorSubject<CachedConclusion[]>([]);

  private readonly CACHE_EXPIRY_MS = 15 * 60 * 1000;

  constructor(private predictiveModelService: PredictiveModelService) {}

  private getLSTMAutoencoderWithCache(meterId: string): Observable<any[]> {
    return new Observable(observer => {
      const cached = this.findCachedPrediction(this.lstmAutoencoderCache$.value, meterId);

      if (cached && this.isCacheValid(cached.lastUpdated)) {
        observer.next(cached.predictions);
        observer.complete();
        return;
      }

      this.predictiveModelService.getLSTMAutoencoderPredictions(meterId).subscribe({
        next: (predictions) => {
          this.updateLSTMAutoencoderCache(meterId, predictions || []);
          observer.next(predictions || []);
          observer.complete();
        },
        error: (error) => {
          console.error('Error getting LSTM Autoencoder predictions:', error);
          observer.next([]);
          observer.complete();
        }
      });
    });
  }

  private getLSTMPredictionsWithCache(meterId: string): Observable<any[]> {
    return new Observable(observer => {
      const cached = this.findCachedPrediction(this.lstmPredictionsCache$.value, meterId);

      if (cached && this.isCacheValid(cached.lastUpdated)) {
        observer.next(cached.predictions);
        observer.complete();
        return;
      }

      this.predictiveModelService.getLSTMPredictions(meterId).subscribe({
        next: (predictions) => {
          this.updateLSTMPredictionsCache(meterId, predictions || []);
          observer.next(predictions || []);
          observer.complete();
        },
        error: (error) => {
          console.error('Error getting LSTM predictions:', error);
          observer.next([]);
          observer.complete();
        }
      });
    });
  }

  getConclusionForMeterAndDate(meterId: string, dateStr: string): Observable<ConclusionResult> {
    return new Observable(observer => {
      const cachedConclusion = this.findCachedConclusion(meterId, dateStr);

      if (cachedConclusion && this.isCacheValid(cachedConclusion.lastUpdated)) {
        observer.next(cachedConclusion.conclusion);
        observer.complete();
        return;
      }

      Promise.all([
        this.getLSTMAutoencoderWithCache(meterId).toPromise(),
        this.getLSTMPredictionsWithCache(meterId).toPromise()
      ]).then(([lstmAutoencoder, lstmPredictions]) => {
        const result = this.calculateConclusionByDate(dateStr, lstmAutoencoder || [], lstmPredictions || []);

        this.updateConclusionCache(meterId, dateStr, result);

        observer.next(result);
        observer.complete();
      }).catch(error => {
        console.error('Error getting conclusion:', error);
        const fallbackResult = { text: 'Chưa có dữ liệu', color: '#9e9e9e' };
        observer.next(fallbackResult);
        observer.complete();
      });
    });
  }


  getTodaysConclusionForMeter(meterId: string): Observable<ConclusionResult> {
    const today = new Date();
    const todayStr = `${today.getDate().toString().padStart(2,'0')}/${(today.getMonth()+1).toString().padStart(2,'0')}/${today.getFullYear()}`;
    return this.getConclusionForMeterAndDate(meterId, todayStr);
  }


  private calculateConclusionByDate(dateStr: string, lstmAutoencoder: any[], lstmPredictions: any[]): ConclusionResult {
    const formatDateFromPrediction = (pred: any): string => {
      const dateString = pred.prediction_time?.$date || pred.prediction_time;
      const predDate = new Date(dateString);
      const day = predDate.getUTCDate().toString().padStart(2, '0');
      const month = (predDate.getUTCMonth() + 1).toString().padStart(2, '0');
      const year = predDate.getUTCFullYear();
      return `${day}/${month}/${year}`;
    };

    const lstmPred = lstmPredictions.find(pred => formatDateFromPrediction(pred) === dateStr);
    const autoencoderPredictions = lstmAutoencoder.filter(pred => formatDateFromPrediction(pred) === dateStr);
    const autoencoderPred = autoencoderPredictions.length > 0 ? this.selectBestPredictionForDay(autoencoderPredictions) : null;

    if (!lstmPred && !autoencoderPred) {
      return { text: 'Chưa có dữ liệu', color: '#9e9e9e' };
    }

    const getScore = (pred: any): number => {
      if (!pred) return 0;
      if (pred.predicted_label === 'normal') return 0;
      if (pred.predicted_label === 'leak') {
        if (pred.confidence === 'NNthap') return 1;
        if (pred.confidence === 'NNTB') return 2;
        if (pred.confidence === 'NNcao') return 3;
        return 1;
      }
      return 0;
    };

    const predictions = [lstmPred, autoencoderPred].filter(p => p !== null);
    if (predictions.length === 0) {
      return { text: 'Chưa có dữ liệu', color: '#9e9e9e' };
    }

    const scores = predictions.map(pred => getScore(pred));
    const averageScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;
    const finalScore = Math.floor(averageScore);

    const getColor = (text: string): string => {
      const colorMap: { [key: string]: string } = {
        'Rò rỉ nghi ngờ cao': '#c62828',
        'Rò rỉ nghi ngờ trung bình': '#f57c00',
        'Rò rỉ nghi ngờ thấp': '#fbc02d',
        'Bình thường': '#2e7d32',
        'Chưa có dữ liệu': '#9e9e9e'
      };
      return colorMap[text] || '#616161';
    };

    let text: string;
    switch (finalScore) {
      case 0: text = 'Bình thường'; break;
      case 1: text = 'Rò rỉ nghi ngờ thấp'; break;
      case 2: text = 'Rò rỉ nghi ngờ trung bình'; break;
      case 3: text = 'Rò rỉ nghi ngờ cao'; break;
      default: text = 'Bình thường'; break;
    }

    return { text, color: getColor(text) };
  }

  private selectBestPredictionForDay(predictions: any[]): any {
    if (predictions.length === 1) return predictions[0];

    const leakPredictions = predictions.filter(p => p.predicted_label === 'leak');
    const candidatePredictions = leakPredictions.length > 0 ? leakPredictions : predictions.filter(p => p.predicted_label === 'normal');
    const confidenceRank: { [key: string]: number } = { 'NNcao': 3, 'NNTB': 2, 'NNthap': 1 };

    candidatePredictions.sort((a, b) => (confidenceRank[b.confidence] || 0) - (confidenceRank[a.confidence] || 0));
    return candidatePredictions[0];
  }

  private findCachedPrediction(cache: CachedPrediction[], meterId: string): CachedPrediction | null {
    return cache.find(item => item.meterId === meterId) || null;
  }

  private findCachedConclusion(meterId: string, dateStr: string): CachedConclusion | null {
    return this.conclusionsCache$.value.find(item =>
      item.meterId === meterId && item.dateStr === dateStr
    ) || null;
  }

  private isCacheValid(lastUpdated: Date): boolean {
    return (Date.now() - lastUpdated.getTime()) < this.CACHE_EXPIRY_MS;
  }

  private updateLSTMAutoencoderCache(meterId: string, predictions: any[]): void {
    const currentCache = this.lstmAutoencoderCache$.value;
    const existingIndex = currentCache.findIndex(item => item.meterId === meterId);

    const newItem: CachedPrediction = {
      meterId,
      predictions,
      lastUpdated: new Date()
    };

    if (existingIndex >= 0) {
      currentCache[existingIndex] = newItem;
    } else {
      currentCache.push(newItem);
    }

    this.lstmAutoencoderCache$.next([...currentCache]);
  }

  private updateLSTMPredictionsCache(meterId: string, predictions: any[]): void {
    const currentCache = this.lstmPredictionsCache$.value;
    const existingIndex = currentCache.findIndex(item => item.meterId === meterId);

    const newItem: CachedPrediction = {
      meterId,
      predictions,
      lastUpdated: new Date()
    };

    if (existingIndex >= 0) {
      currentCache[existingIndex] = newItem;
    } else {
      currentCache.push(newItem);
    }

    this.lstmPredictionsCache$.next([...currentCache]);
  }

  private updateConclusionCache(meterId: string, dateStr: string, conclusion: ConclusionResult): void {
    const currentCache = this.conclusionsCache$.value;
    const existingIndex = currentCache.findIndex(item =>
      item.meterId === meterId && item.dateStr === dateStr
    );

    const newItem: CachedConclusion = {
      meterId,
      dateStr,
      conclusion,
      lastUpdated: new Date()
    };

    if (existingIndex >= 0) {
      currentCache[existingIndex] = newItem;
    } else {
      currentCache.push(newItem);
    }

    this.conclusionsCache$.next([...currentCache]);
  }

  getLSTMAutoencoderCache(): Observable<CachedPrediction[]> {
    return this.lstmAutoencoderCache$.asObservable();
  }

  getLSTMPredictionsCache(): Observable<CachedPrediction[]> {
    return this.lstmPredictionsCache$.asObservable();
  }

  getConclusionsCache(): Observable<CachedConclusion[]> {
    return this.conclusionsCache$.asObservable();
  }

  clearCache(): void {
    this.lstmAutoencoderCache$.next([]);
    this.lstmPredictionsCache$.next([]);
    this.conclusionsCache$.next([]);
  }

  refreshMeterCache(meterId: string): void {
    const autoencoderCache = this.lstmAutoencoderCache$.value.filter(item => item.meterId !== meterId);
    const predictionsCache = this.lstmPredictionsCache$.value.filter(item => item.meterId !== meterId);
    const conclusionsCache = this.conclusionsCache$.value.filter(item => item.meterId !== meterId);

    this.lstmAutoencoderCache$.next(autoencoderCache);
    this.lstmPredictionsCache$.next(predictionsCache);
    this.conclusionsCache$.next(conclusionsCache);
  }

  preloadCacheForMeters(meterIds: string[]): Observable<boolean> {
    return new Observable(observer => {
      const metersToLoad = meterIds.filter(meterId => {
        const autoencoderCache = this.findCachedPrediction(this.lstmAutoencoderCache$.value, meterId);
        const predictionsCache = this.findCachedPrediction(this.lstmPredictionsCache$.value, meterId);

        return !autoencoderCache || !this.isCacheValid(autoencoderCache.lastUpdated) ||
               !predictionsCache || !this.isCacheValid(predictionsCache.lastUpdated);
      });

      if (metersToLoad.length === 0) {
        observer.next(true);
        observer.complete();
        return;
      }

      console.log(`Preloading cache for ${metersToLoad.length} meters...`);

      this.preloadMetersBatch(metersToLoad, 0, observer);
    });
  }

  private preloadMetersBatch(meterIds: string[], index: number, observer: any): void {
    if (index >= meterIds.length) {
      observer.next(true);
      observer.complete();
      return;
    }

    const meterId = meterIds[index];

    Promise.all([
      this.getLSTMAutoencoderWithCache(meterId).toPromise(),
      this.getLSTMPredictionsWithCache(meterId).toPromise()
    ]).then(() => {
      setTimeout(() => {
        this.preloadMetersBatch(meterIds, index + 1, observer);
      }, 100);
    }).catch(error => {
      console.error(`Error preloading meter ${meterId}:`, error);
      setTimeout(() => {
        this.preloadMetersBatch(meterIds, index + 1, observer);
      }, 100);
    });
  }

  getTodaysConclusionsForMeters(meterIds: string[]): Observable<{[meterId: string]: ConclusionResult}> {
    return new Observable(observer => {
      const today = new Date();
      const todayStr = `${today.getDate().toString().padStart(2,'0')}/${(today.getMonth()+1).toString().padStart(2,'0')}/${today.getFullYear()}`;

      this.preloadCacheForMeters(meterIds).subscribe(() => {
        const conclusionPromises = meterIds.map(meterId =>
          this.getConclusionForMeterAndDate(meterId, todayStr).toPromise()
            .then(conclusion => ({ meterId, conclusion }))
        );

        Promise.all(conclusionPromises).then(results => {
          const conclusionsMap: {[meterId: string]: ConclusionResult} = {};
          results.forEach(result => {
            if (result && result.conclusion) {
              conclusionsMap[result.meterId] = result.conclusion;
            }
          });

          observer.next(conclusionsMap);
          observer.complete();
        }).catch(error => {
          console.error('Error getting conclusions for meters:', error);
          observer.next({});
          observer.complete();
        });
      });
    });
  }
}
