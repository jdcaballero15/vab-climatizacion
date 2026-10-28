import type { components } from "../../api/schema";

export type UserAdmin = components["schemas"]["UserAdminOut"];
export type UserCreate = components["schemas"]["UserCreate"];
export type UserRole = UserAdmin["role"];
export type PasswordReset = components["schemas"]["PasswordResetOut"];
