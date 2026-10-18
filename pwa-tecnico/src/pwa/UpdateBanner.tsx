interface UpdateBannerProps {
  show: boolean;
  onUpdate: () => void;
}

// Presentacional: avisa al técnico que hay una versión nueva y ofrece aplicarla.
export function UpdateBanner({ show, onUpdate }: UpdateBannerProps) {
  if (!show) {
    return null;
  }

  return (
    <div className="update-banner" role="alert">
      <span>Hay una nueva versión disponible.</span>
      <button type="button" onClick={onUpdate}>
        Actualizar
      </button>
    </div>
  );
}
