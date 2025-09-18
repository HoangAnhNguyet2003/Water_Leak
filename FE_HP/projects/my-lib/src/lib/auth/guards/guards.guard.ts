import { inject } from '@angular/core';
import { CanActivateFn, ActivatedRouteSnapshot, RouterStateSnapshot, Router, UrlTree } from '@angular/router';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { AuthService } from '../service/auth.service';

export const authGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree => {

  const authService = inject(AuthService);
  const router = inject(Router);

  console.log('🔍 AuthGuardFn - Checking access for route:', state.url);
  return authService.checkAuthStatus(true).pipe(
    map(user => {
      if (user) {
        console.log('✅ AuthGuardFn - Authentication confirmed by backend, checking role...');
        return checkRoleAccess(user, route, authService, router);
      } else {
        console.log('❌ AuthGuardFn - Not authenticated, redirecting to login...');
        return redirectToLogin(state.url, authService, router);
      }
    }),
    catchError(error => {
      console.log('❌ AuthGuardFn - Authentication check failed, redirecting to login...');
      return of(redirectToLogin(state.url, authService, router));
    })
  );
};

function checkRoleAccess(user: any, route: ActivatedRouteSnapshot, authService: AuthService, router: Router): boolean | UrlTree {
  console.log('🔍 AuthGuardFn - Current user:', user);
  console.log('🔍 AuthGuardFn - Route data:', route.data);

  const requiredRole = route.data?.['role'];
  if (requiredRole) {
    console.log('🔍 AuthGuardFn - Route requires role:', requiredRole);

    if (requiredRole === 'admin' && !authService.isAdmin()) {
      console.log('❌ AuthGuardFn - User is not admin, redirecting to login...');
      return redirectToLogin(undefined, authService, router);
    }

    if (requiredRole === 'branch' && !authService.isBranch()) {
      console.log('❌ AuthGuardFn - User is not branch manager, redirecting to login...');
      return redirectToLogin(undefined, authService, router);
    }
    
    if (requiredRole === 'company' && !authService.isCompany()) {
      console.log('❌ AuthGuardFn - User is not company manager, redirecting to login...');
      return redirectToLogin(undefined, authService, router);
    }
  }

  console.log('✅ AuthGuardFn - Access granted');
  return true;
}

function redirectToLogin(returnUrl: string | undefined, authService: AuthService, router: Router): UrlTree {
  console.log('🔄 AuthGuardFn - Redirecting to login');

  if (returnUrl) {
    sessionStorage.setItem('returnUrl', encodeURIComponent(returnUrl));
  }
  const baseUrl = window.location.origin;
  const loginUrl = `${baseUrl}/auth/login`;
  const params = returnUrl ? `?returnUrl=${encodeURIComponent(returnUrl)}` : '';

  return router.createUrlTree(['/auth/login'], {
    queryParams: returnUrl ? { returnUrl: encodeURIComponent(returnUrl) } : {}
  });
}
