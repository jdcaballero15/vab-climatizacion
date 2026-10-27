// Access token en memoria. Lo setean el login y la renovación, y lo lee el cliente de API.
// El refresh token no pasa por acá: vive en una cookie httpOnly (ADR 0010, E01-07).
let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}
