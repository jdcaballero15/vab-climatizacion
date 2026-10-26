// Tokens de la sesión en memoria. Los setea el login y los lee el cliente de API.
// El access token viaja en cada request; el refresh token sirve para renovarlo.
let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function setRefreshToken(token: string | null): void {
  refreshToken = token;
}

export function getRefreshToken(): string | null {
  return refreshToken;
}
