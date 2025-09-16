
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  refreshToken: string;
  roleId: string;
  user: UserInfo;
}

export interface UserInfo {
  id: string;
  username: string;
  roleId: string;
  roleName: string;
  companyId?: string;
  branchId?: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: UserInfo | null;
  loading: boolean;
  error: string | null;
}

// ===== API RESPONSE INTERFACES =====

export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  message?: string;
}

export interface MeResponse {
  id: string;
  username: string;
  roleId: string;
  roleName: string;
  companyId?: string;
  branchId?: string;
  authenticated: boolean;
}
