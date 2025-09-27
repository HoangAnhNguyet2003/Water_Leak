import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, BehaviorSubject, throwError, of, switchMap } from 'rxjs';
import { catchError, tap, map, timeout, finalize, mergeMap } from 'rxjs/operators';
import { LoginRequest, UserInfo, AuthState, MeResponse } from '../models/auth.interface';
import { environment } from '../../enviroments/enviroment';
import { retry } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly API_BASE_URL = environment.apiUrl;
  private readonly CACHE_TTL = 5 * 60 * 1000;
  private readonly UNAUTH_CACHE_TTL = 30 * 1000;

  private http = inject(HttpClient);

  private authStateSubject = new BehaviorSubject<AuthState>({
    isAuthenticated: false,
    user: null,
    loading: false,
    error: null
  });

  private authCache: {
    user: UserInfo | null;
    timestamp: number;
    ttl: number;
  } | null = null;

  public authState$ = this.authStateSubject.asObservable();

  constructor() { }

   /**
   * Login user with username and password
   */
  login(credentials: LoginRequest): Observable<UserInfo> {
    console.log('🔍 AuthService - Attempting login for:', credentials.username);

    this.setLoading(true);
    this.clearError();

    return this.http.post<any>(`${this.API_BASE_URL}/auth/role-based-login`, credentials, {
      withCredentials: true
    }).pipe(
      retry(1),
      timeout(10000),
      map(response => {
        console.log('✅ AuthService - Login success:', response);

        if (response && response.user) {
          const user: UserInfo = {
            id: response.user.id,
            username: response.user.username,
            roleId: response.roleId || response.user.roleId,
            roleName: response.user.roleName,
            companyId: response.companyId || null,
            branchId: response.branchId || null
          };

          this.invalidateAuthCache();
          this.setAuthenticatedUser(user);
          return user;
        }

        throw new Error('Invalid login response format');
      }),
      catchError(err => {
        console.error('❌ AuthService - Login failed:', err);
        this.setError(this.getErrorMessage(err));
        this.setLoading(false);
        return throwError(() => err);
      })
    );
  }

  /**
   * Logout user
   */
  logout(): Observable<void> {
    console.log('🔍 AuthService - Logging out...');

    return this.http.post<void>(`${this.API_BASE_URL}/auth/logout`, {}, {
      withCredentials: true
    }).pipe(
      tap(() => {
        console.log('✅ AuthService - Logout success');
        this.invalidateAuthCache();
        this.clearAuthState();
      }),
      catchError(err => {
        console.error('⚠️ AuthService - Logout error, clearing state anyway:', err);
        this.clearAuthState();
        return throwError(() => err);
      })
    );
  }

  /**
   * Check authentication status with backend
   */
  checkAuthStatus(forceRefresh = false): Observable<UserInfo | null> {
    console.log('🔍 AuthService - Checking auth status, forceRefresh:', forceRefresh);

    const now = Date.now();

    if (!forceRefresh && this.authCache && (now - this.authCache.timestamp) < this.authCache.ttl) {
      console.log('✅ AuthService - Using cached auth status');
      const cachedUser = this.authCache.user;
      cachedUser ? this.setAuthenticatedUser(cachedUser) : this.clearAuthState();
      return of(cachedUser);
    }

    console.log('🔍 AuthService - Checking with backend...');
    this.setLoading(true);

    return this.http.get<MeResponse>(`${this.API_BASE_URL}/auth/me`, {
      withCredentials: true
    }).pipe(
      retry(1),
      timeout(10000),

      map(response => {
        console.log('✅ AuthService - Backend response:', response);

        if (response && response.authenticated && response.id) {
          const user: UserInfo = {
            id: response.id,
            username: response.username,
            roleId: response.roleId,
            roleName: response.roleName,
            companyId: response.companyId || undefined,
            branchId: response.branchId || undefined
          };

          this.setAuthenticatedUser(user);
          this.authCache = { user, timestamp: now, ttl: this.CACHE_TTL };
          console.log('✅ AuthService - User authenticated:', user.username);
          return user;
        } else {
          console.log('ℹ️ AuthService - User not authenticated');
          this.clearAuthState();
          this.authCache = { user: null, timestamp: now, ttl: this.UNAUTH_CACHE_TTL };
          return null;
        }
      }),
      catchError(err => {
        console.error('❌ AuthService - Auth check failed:', err.status, err.message);
        this.clearAuthState();

        const cacheTtl = err.status === 401 ? 60 * 1000 : 10 * 1000;
        this.authCache = { user: null, timestamp: now, ttl: cacheTtl };

        return of(null);
      }),
      finalize(() => this.setLoading(false))
    );
  }

  /**
   * Refresh authentication token
   */
  refreshToken(): Observable<UserInfo> {
    console.log('🔍 AuthService - Refreshing token...');
    return this.http.post(`${this.API_BASE_URL}/auth/refresh`, {}, { withCredentials: true }).pipe(
      retry(1),
      timeout(10000),
      switchMap(() => this.checkAuthStatus(true).pipe(
        map(user => {
          if (!user) throw new Error('Failed to get user info after refresh');
          return user;
        })
      )),
      catchError(err => {
        console.error('❌ AuthService - Token refresh failed:', err);
        this.clearAuthState();
        return throwError(() => err);
      }),
      finalize(() => this.setLoading(false))
    );
  }

  // ===== UTILITY METHODS =====

  /**
   * Get current user
   */
  getCurrentUser(): UserInfo | null {
    return this.authStateSubject.value.user;
  }

  /**
   * Check if user is admin
   */
  isAdmin(): boolean {
    const user = this.getCurrentUser();
    return user?.roleName?.toLowerCase() === 'admin';
  }

  /**
   * Check if user is branch manager
   */
  isBranch(): boolean {
    const user = this.getCurrentUser();
    const role = user?.roleName?.toLowerCase();
    return role === 'branch' || role === 'branch_manager';
  }

   /**
   * Check if user is company manager
   */
  isCompany(): boolean {
    const user = this.getCurrentUser();
    const role = user?.roleName?.toLowerCase();
    return role === 'company' || role === 'company_manager';
  }

  /**
   * Check if user has specific role
   */
  hasRole(roleName: string): boolean {
    const user = this.getCurrentUser();
    return user?.roleName?.toLowerCase() === roleName.toLowerCase();
  }

  /**
   * Invalidate auth cache
   */
  invalidateAuthCache(): void {
    console.log('🔄 AuthService - Cache invalidated');
    this.authCache = null;
  }

  public resetAuth(): void {
    this.logout().subscribe({
      next: () => {
        console.log('✅ AuthService - Logout completed, state cleared');
      },
      error: (err) => {
        console.error('❌ AuthService - Logout failed, but state cleared anyway:', err);
      }
    });
    this.clearAuthState();
    this.invalidateAuthCache();
  }

  // ===== PRIVATE STATE MANAGEMENT =====

  private setAuthenticatedUser(user: UserInfo): void {
    this.authStateSubject.next({
      isAuthenticated: true,
      user,
      loading: false,
      error: null
    });
  }

  private clearAuthState(): void {
    this.authStateSubject.next({
      isAuthenticated: false,
      user: null,
      loading: false,
      error: null
    });
  }

  private setLoading(loading: boolean): void {
    this.authStateSubject.next({
      ...this.authStateSubject.value,
      loading
    });
  }

  private setError(error: string): void {
    this.authStateSubject.next({
      ...this.authStateSubject.value,
      error,
      loading: false
    });
  }

  private clearError(): void {
    if (this.authStateSubject.value.error) {
      this.authStateSubject.next({
        ...this.authStateSubject.value,
        error: null
      });
    }
  }

  private getErrorMessage(err: HttpErrorResponse): string {
    // Try to extract a meaningful message from various server error shapes
    const extractMessage = (obj: any, depth = 0): string | null => {
      if (!obj || typeof obj !== 'object' || depth > 4) return null;
      if (typeof obj.message === 'string' && obj.message.trim().length > 0) return obj.message;
      for (const key of Object.keys(obj)) {
        const val = obj[key];
        if (typeof val === 'string' && key.toLowerCase().includes('message')) return val;
        if (typeof val === 'object') {
          const found = extractMessage(val, depth + 1);
          if (found) return found;
        }
      }
      return null;
    };

    const serverMessage = extractMessage(err.error) || extractMessage(err) || null;
    if (serverMessage) return serverMessage;

    // Fallbacks
    if (err.status === 401 || err.status === 400) return 'Sai tên đăng nhập hoặc mật khẩu';
    if (err.status === 0) return 'Không thể kết nối đến server';
    return 'Đã xảy ra lỗi, vui lòng thử lại';
  }
}
