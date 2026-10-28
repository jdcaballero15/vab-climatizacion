import { api } from "../../api/client";

/** Máximo de fotos por cierre (E05-06, criterio 2). El backend valida lo mismo. */
export const MAX_PHOTOS = 5;

const MAX_SIDE = 1600;
const JPEG_QUALITY = 0.8;
const PHOTO_TYPE = "image/jpeg";

/** Qué se sube: el propósito y el tipo que acepta la API para cada uno (E00-09). */
interface FileKind {
  purpose: "closure_photo" | "closure_signature";
  contentType: string;
}

const PHOTO: FileKind = { purpose: "closure_photo", contentType: PHOTO_TYPE };
/** La firma del cliente (E05-07): la API la acepta solo en PNG. */
export const SIGNATURE: FileKind = { purpose: "closure_signature", contentType: "image/png" };

/** Una foto del cierre, desde que se elige hasta que queda confirmada en el bucket. */
export interface ClosurePhoto {
  key: string;
  blob: Blob;
  previewUrl: string;
  /** Id del archivo en la API, una vez subido al bucket. */
  fileId: string | null;
  /** Confirmada por la API: lista para ir en el cierre. */
  uploaded: boolean;
}

const NO_CONNECTION = "No se pudo subir una foto. Revisá la conexión e intentá de nuevo.";

/** Error con un mensaje para mostrarle al técnico. */
export class PhotoUploadError extends Error {
  /** Sin señal o el servidor caído: se puede reintentar más tarde (E05-13). */
  get offline(): boolean {
    return this.message === NO_CONNECTION;
  }
}

/** Tamaño con el lado mayor en 1600 px como máximo, sin agrandar las fotos chicas. */
export function scaledSize(width: number, height: number) {
  const scale = Math.min(1, MAX_SIDE / Math.max(width, height));
  return { width: Math.round(width * scale), height: Math.round(height * scale) };
}

/**
 * Achica la foto en el celular antes de subirla: las de la cámara pesan varios MB y
 * la señal en obra suele ser mala. `from-image` respeta la rotación de la cámara.
 */
export async function compressImage(file: Blob): Promise<Blob> {
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    throw new PhotoUploadError("No se pudo abrir la foto. Probá con otra.");
  }
  try {
    const { width, height } = scaledSize(bitmap.width, bitmap.height);
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    canvas.getContext("2d")?.drawImage(bitmap, 0, 0, width, height);
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, PHOTO_TYPE, JPEG_QUALITY),
    );
    if (!blob) {
      throw new PhotoUploadError("No se pudo preparar la foto. Probá con otra.");
    }
    return blob;
  } finally {
    bitmap.close();
  }
}

/** Lo que hace falta para subir una foto: la del formulario o la guardada en el celular. */
type UploadablePhoto = Pick<ClosurePhoto, "key" | "blob" | "fileId" | "uploaded">;
type SavePhoto = (key: string, changes: Partial<UploadablePhoto>) => void;

/**
 * Sube las fotos que falten y devuelve sus ids en el orden del formulario. Cada paso
 * hecho se guarda con `save`: si se corta la señal, el reintento sigue desde ahí y no
 * vuelve a subir lo que ya llegó (E05-06, criterio 5).
 */
export async function uploadPhotos(photos: UploadablePhoto[], save: SavePhoto): Promise<string[]> {
  const ids: string[] = [];
  for (const photo of photos) {
    ids.push(await uploadOne(photo, save));
  }
  return ids;
}

/**
 * Sube una sola imagen y devuelve su id. Mismos pasos que las fotos: si ya llegó no se
 * vuelve a subir. Sirve para la firma del cliente con `SIGNATURE`.
 */
export async function uploadOne(
  photo: UploadablePhoto,
  save: SavePhoto,
  kind: FileKind = PHOTO,
): Promise<string> {
  if (photo.fileId && photo.uploaded) {
    return photo.fileId;
  }
  const fileId = photo.fileId ?? (await sendToBucket(photo, save, kind));
  await confirm(photo.key, fileId, save);
  return fileId;
}

async function sendToBucket(
  photo: UploadablePhoto,
  save: SavePhoto,
  kind: FileKind,
): Promise<string> {
  const { data, error, response } = await guard(() =>
    api.POST("/files", {
      body: { purpose: kind.purpose, content_type: kind.contentType, size_bytes: photo.blob.size },
    }),
  );
  if (!data) {
    throw new PhotoUploadError(apiMessage(error, response.status));
  }
  // Directo al bucket con la URL firmada: sin el token de la API y con el tipo firmado.
  const put = await guard(() =>
    globalThis.fetch(data.upload_url, {
      method: "PUT",
      headers: { "Content-Type": kind.contentType },
      body: photo.blob,
    }),
  );
  if (!put.ok) {
    throw new PhotoUploadError(NO_CONNECTION);
  }
  save(photo.key, { fileId: data.file_id });
  return data.file_id;
}

async function confirm(key: string, fileId: string, save: SavePhoto): Promise<void> {
  const { data, error, response } = await guard(() =>
    api.POST("/files/{file_id}/confirm", { params: { path: { file_id: fileId } } }),
  );
  if (!data) {
    // El bucket no tiene el archivo (o la API ya no lo reconoce): se sube de nuevo.
    if (response.status === 422 || response.status === 404) {
      save(key, { fileId: null });
    }
    throw new PhotoUploadError(apiMessage(error, response.status));
  }
  save(key, { uploaded: true });
}

/** Una caída de red llega como excepción: se muestra como problema de conexión. */
async function guard<T>(call: () => Promise<T>): Promise<T> {
  try {
    return await call();
  } catch {
    throw new PhotoUploadError(NO_CONNECTION);
  }
}

function apiMessage(error: unknown, status: number): string {
  const message = (error as { detail?: { message?: unknown } } | undefined)?.detail?.message;
  if (status === 422 && typeof message === "string") {
    return message;
  }
  return NO_CONNECTION;
}
