/** El nombre ya existe (activo o desactivado): el backend responde 409. */
export class NameTakenError extends Error {}

/** Error de guardado de un catálogo: distingue el nombre repetido del resto. */
export function catalogSaveError(status: number | undefined, message: string): Error {
  return status === 409 ? new NameTakenError() : new Error(message);
}
