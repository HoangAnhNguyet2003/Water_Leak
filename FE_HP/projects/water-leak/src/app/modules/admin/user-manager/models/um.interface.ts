import { WaterMeter } from "../../meter-manager/models";

export interface Branch {
  id: string;
  name: string;
  address: string;
}

export type UserData = {
  id: string;
  username: string;
  roleName: UserRole | string;
  branchId?: string;
  isActive: boolean;
  branchName?: string;
  lastLogin?: string | null;
  password?: string;
  managedWaterMeter?: WaterMeter[];
};

export enum UserRole {
  'Admin' = 'admin',
  'Company' = 'company_manager',
  'Branch' = 'branch_manager'
}

export enum UserStatus {
  Active = 1,
  Inactive = 0
}
