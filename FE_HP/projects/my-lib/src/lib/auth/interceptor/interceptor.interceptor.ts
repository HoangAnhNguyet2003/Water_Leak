import { Injectable, inject } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError, BehaviorSubject } from 'rxjs';
import { catchError, switchMap, filter, take } from 'rxjs/operators';
import { AuthService } from '../service/auth.service';
import { Router } from '@angular/router';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private authService = inject(AuthService);
  private router = inject(Router);

  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<any> = new BehaviorSubject<any>(null);

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    console.debug('[AuthInterceptor] intercept called for', req.method, req.url);

    let modifiedReq = req.clone({ withCredentials: true });

    const isMutating = ['POST','PUT','PATCH','DELETE'].includes(req.method);
    if (isMutating || this.isRefreshEndpoint(req.url)) {
      const csrfName = this.isRefreshEndpoint(req.url) ? 'csrf_refresh_token' : 'csrf_access_token';
      const csrfVal = this.getCookie(csrfName);
      console.debug(`[AuthInterceptor] cookie ${csrfName}:`, csrfVal);
      if (csrfVal) {
        modifiedReq = modifiedReq.clone({
          headers: modifiedReq.headers.set('X-CSRF-TOKEN', csrfVal)
        });
        console.debug('[AuthInterceptor] attached X-CSRF-TOKEN header');
      } else {
        console.debug('[AuthInterceptor] CSRF not found, header not attached');
      }
    }

    return next.handle(modifiedReq).pipe(
      catchError((error: HttpErrorResponse) => {
        console.debug('[AuthInterceptor] response error', error.status, req.url);
        if (error.status === 401 && !this.isAuthEndpoint(req.url)) {
          return this.handle401Error(modifiedReq, next);
        }
        if (error.status === 403) {
          console.log('🔒 AuthInterceptor - 403 Forbidden - Access denied');
        }
        return throwError(() => error);
      })
    );
  }

  private handle401Error(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    console.debug('[AuthInterceptor] handle401Error called');
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      this.refreshTokenSubject.next(null);
      console.log('🔄 AuthInterceptor - start refresh');
      return this.authService.refreshToken().pipe(
        switchMap(() => {
          this.isRefreshing = false;
          this.refreshTokenSubject.next(true);
          console.log('✅ AuthInterceptor - refresh ok, retrying request');
          let retryReq = request.clone({ withCredentials: true });
          if (['POST','PUT','PATCH','DELETE'].includes(request.method)) {
            const csrf = this.getCookie('csrf_access_token');
            if (csrf) retryReq = retryReq.clone({ headers: retryReq.headers.set('X-CSRF-TOKEN', csrf) });
          }
          return next.handle(retryReq);
        }),
        catchError((err) => {
          this.isRefreshing = false;
          this.refreshTokenSubject.next(null);
          console.log('❌ AuthInterceptor - refresh failed', err);
          this.authService.resetAuth();
          this.router.navigate(['/login']);
          return throwError(() => err);
        })
      );
    } else {
      return this.refreshTokenSubject.pipe(
        filter(token => token != null),
        take(1),
        switchMap(() => {
          console.debug('[AuthInterceptor] waiting for refresh then retry');
          return next.handle(request.clone({ withCredentials: true }));
        })
      );
    }
  }

  private isAuthEndpoint(url: string): boolean {
    const authEndpoints = ['/auth/login', '/auth/role-based-login', '/auth/refresh', '/auth/logout', '/auth/me'];
    return authEndpoints.some(endpoint => url.includes(endpoint));
  }

  private isRefreshEndpoint(url: string): boolean {
    return url.includes('/auth/refresh');
  }

  private getCookie(name: string): string | null {
    const match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? decodeURIComponent(match.pop() || '') : null;
  }
}
