import type { SiteCreate } from "./types";

interface SiteFieldsProps {
  idPrefix: string;
  values: SiteCreate;
  onChange: (values: SiteCreate) => void;
}

/** Campos de un domicilio; los usan la ficha del cliente y el alta de órdenes. */
export function SiteFields({ idPrefix, values, onChange }: SiteFieldsProps) {
  const id = (field: string) => `${idPrefix}-${field}`;
  return (
    <>
      <label htmlFor={id("label")}>Etiqueta</label>
      <input
        id={id("label")}
        value={values.label ?? ""}
        onChange={(event) => onChange({ ...values, label: event.target.value || null })}
        placeholder="Sede central, depósito"
        maxLength={255}
      />
      <label htmlFor={id("address")}>Dirección</label>
      <input
        id={id("address")}
        value={values.address}
        onChange={(event) => onChange({ ...values, address: event.target.value })}
        placeholder="Calle y número, localidad"
        maxLength={255}
      />
      <label htmlFor={id("reference")}>Referencia</label>
      <input
        id={id("reference")}
        value={values.reference ?? ""}
        onChange={(event) => onChange({ ...values, reference: event.target.value || null })}
        placeholder="Piso, departamento, cómo llegar"
        maxLength={500}
      />
    </>
  );
}
