import { Branch, UserData, UserRole } from '../models';
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { catchError, map, switchMap, take } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class UmServicesService {
  private readonly API_BASE = 'http://localhost:5000/api/v1';
  private users$ = new BehaviorSubject<UserData[]>([]);
  private branch$ = new BehaviorSubject<Branch[]>([]);

  getAllUsers(force = false): Observable<UserData[]> {
    if (!this.users$.value.length || force) {
      this.http.get<{ items: any[] }>(`${this.API_BASE}/users/all`).pipe(
        map(res => res.items.map(item => this.mapFromApi(item)))
      ).subscribe(data => this.users$.next(data));
    }
    return this.users$.asObservable();
  }

  getAllBranches(force = false): Observable<Branch[]> {
    if (!this.branch$.value.length || force) {
      this.http.get<{ items: any[] }>(`${this.API_BASE}/branches/get_all`).pipe(
        map(res => res.items || []),
        catchError(err => {
          console.error('Failed to fetch branches', err);
          return of([] as any[]);
        })
      ).subscribe(data => this.branch$.next(data));
    }
    return this.branch$.asObservable();
  }

  createUser(user: Partial<UserData>): Observable<{ success: boolean, error?: any }> {
    return this.http.post<any>(`${this.API_BASE}/users/add`, user).pipe(
      switchMap(() =>
        this.getAllUsers(true).pipe(
          take(1),
          map(() => ({ success: true })),
          catchError(err => of({ success: false, error: err }))
        )
      ),
      catchError(err => of({ success: false, error: err }))
    );
  }

  updateUser(userId: string, user: Partial<UserData>): Observable<{ success: boolean, error?: any }> {
    return this.http.patch<any>(`${this.API_BASE}/users/update/${userId}`, user).pipe(
      map(() => {
        this.getAllUsers(true);
        return { success: true };
      }),
      catchError(err => {
        console.error('Error updating user:', err);
        return of({ success: false, error: err });
      })
    );
  }


  deleteUser(userId: string): Observable<{ success: boolean, error?: any }> {
    return this.http.delete<void>(`${this.API_BASE}/users/delete/${userId}`).pipe(
      map(() => {
        this.getAllUsers(true);
        return { success: true };
      }),
      catchError((err) => {
        console.error('Error deleting user:', err);
        return of({ success: false, error: err }); // Return error in a structured way
      })
    );
  }


  private mapFromApi(apiUser: any): UserData {
    return {
      id: String(apiUser.id),
      username: apiUser.username,
      roleName: apiUser.roleName as UserRole,
      branchName: apiUser.branchName,
      isActive: Boolean(apiUser.isActive),
      lastLogin: apiUser.lastLogin,
      managedWaterMeter: apiUser.managedWaterMeter || []
    };
  }
  constructor(private http: HttpClient) { }
}
