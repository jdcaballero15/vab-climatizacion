import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  subtitle?: ReactNode;
  titleId?: string;
  /** Acciones de la pantalla (por ejemplo, el botón para crear), alineadas a la derecha. */
  actions?: ReactNode;
}

/** Etiqueta en mayúsculas, título y una bajada: el encabezado de cada pantalla. */
export function PageHeader({ eyebrow, title, subtitle, titleId, actions }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header__row">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2 id={titleId}>{title}</h2>
          {subtitle && <p className="page-header__subtitle">{subtitle}</p>}
        </div>
        {actions}
      </div>
    </header>
  );
}
