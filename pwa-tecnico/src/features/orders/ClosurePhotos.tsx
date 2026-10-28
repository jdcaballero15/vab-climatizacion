import { Camera, ImagePlus, X } from "lucide-react";
import type { ChangeEvent } from "react";

import { MAX_PHOTOS, type ClosurePhoto } from "./photos";

const FULL_NOTICE = `Podés adjuntar hasta ${MAX_PHOTOS} fotos.`;

interface ClosurePhotosProps {
  photos: ClosurePhoto[];
  /** Fotos que se están comprimiendo. */
  adding: boolean;
  /** Aviso de la sección: el máximo o una foto que no se pudo abrir. */
  notice: string | null;
  disabled: boolean;
  onAdd: (files: File[]) => void;
  onRemove: (key: string) => void;
}

/** Fotos del cierre (E05-06): de la cámara o de la galería, con miniatura para quitarlas. */
export function ClosurePhotos({
  photos,
  adding,
  notice,
  disabled,
  onAdd,
  onRemove,
}: ClosurePhotosProps) {
  const full = photos.length >= MAX_PHOTOS;
  const blocked = disabled || adding || full;
  const message = notice ?? (full ? FULL_NOTICE : null);

  const pick = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    // Permite volver a elegir el mismo archivo después de quitarlo.
    event.target.value = "";
    if (files.length > 0) {
      onAdd(files);
    }
  };

  return (
    <>
      {photos.length > 0 && (
        <ul className="closure__photos">
          {photos.map((photo, index) => (
            <li key={photo.key} className="closure__photo">
              <img src={photo.previewUrl} alt={`Foto ${index + 1}`} />
              <button
                type="button"
                className="closure__photo-remove"
                aria-label={`Quitar foto ${index + 1}`}
                disabled={disabled}
                onClick={() => onRemove(photo.key)}
              >
                <X size={18} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="closure__photo-actions">
        <label className="closure__photo-button" aria-disabled={blocked || undefined}>
          <Camera size={20} aria-hidden="true" />
          Sacar foto
          <input
            type="file"
            accept="image/*"
            capture="environment"
            className="visually-hidden"
            disabled={blocked}
            onChange={pick}
          />
        </label>
        <label className="closure__photo-button" aria-disabled={blocked || undefined}>
          <ImagePlus size={20} aria-hidden="true" />
          Elegir de la galería
          <input
            type="file"
            accept="image/*"
            multiple
            className="visually-hidden"
            disabled={blocked}
            onChange={pick}
          />
        </label>
      </div>
      {adding && <p className="closure__hint">Preparando la foto…</p>}
      {message && <p className="closure__hint">{message}</p>}
    </>
  );
}
