import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { PageHeader } from "../../app/PageHeader";

type Preview = components["schemas"]["CsvPreviewOut"];
type Catalog = "work-types" | "equipment-types" | "failures" | "repairs" | "parts";

const CATALOGS: Record<Catalog, string> = {
  "work-types": "Tipos de trabajo",
  "equipment-types": "Tipos de equipo",
  failures: "Fallas",
  repairs: "Reparaciones",
  parts: "Materiales",
};

function saveError(error: unknown, fallback: string): Error {
  const detail = (error as { detail?: { message?: unknown } } | undefined)?.detail;
  return new Error(typeof detail?.message === "string" ? detail.message : fallback);
}

/** El archivo como texto, con FileReader: anda en todos los navegadores de la oficina. */
function readText(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(new Error("No se pudo leer el archivo."));
    reader.readAsText(file, "utf-8");
  });
}

/**
 * Cargas masivas por CSV (E02-08): se descarga el catálogo, se edita en una planilla y se
 * vuelve a subir. Antes de aplicar se ven altas, cambios y errores; con errores no se
 * aplica nada.
 */
export function CatalogCsvPage() {
  const queryClient = useQueryClient();
  const [catalog, setCatalog] = useState<Catalog>("parts");
  const [content, setContent] = useState<string | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);

  const download = useMutation<void, Error>({
    mutationFn: async () => {
      const { data, error } = await api.GET("/admin/catalog-csv/{catalog}", {
        params: { path: { catalog } },
        parseAs: "blob",
      });
      if (error || !data) {
        throw new Error("No se pudo descargar el catálogo.");
      }
      const url = URL.createObjectURL(data as Blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${catalog}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    },
  });
  const send = useMutation<Preview, Error, "preview" | "apply">({
    mutationFn: async (step) => {
      const body = { content: content ?? "" };
      const params = { path: { catalog } };
      const { data, error } =
        step === "preview"
          ? await api.POST("/admin/catalog-csv/{catalog}/preview", { params, body })
          : await api.POST("/admin/catalog-csv/{catalog}/apply", { params, body });
      if (error || !data) {
        throw saveError(error, "No se pudo leer el archivo.");
      }
      return data;
    },
    onSuccess: async (data) => {
      setPreview(data);
      if (data.applied) {
        await queryClient.invalidateQueries();
      }
    },
  });

  return (
    <section className="catalog">
      <PageHeader
        eyebrow="Catálogos"
        title="Importar y exportar"
        subtitle="Descargá un catálogo, editalo en una planilla y volvé a subirlo."
      />
      <div className="clients__filters">
        <label>
          Catálogo{" "}
          <select
            value={catalog}
            onChange={(event) => {
              setCatalog(event.target.value as Catalog);
              setPreview(null);
            }}
          >
            {(Object.keys(CATALOGS) as Catalog[]).map((value) => (
              <option key={value} value={value}>
                {CATALOGS[value]}
              </option>
            ))}
          </select>
        </label>
        <button type="button" disabled={download.isPending} onClick={() => download.mutate()}>
          Descargar CSV
        </button>
      </div>
      <div className="clients__filters">
        <label>
          Archivo para importar{" "}
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={async (event) => {
              const file = event.target.files?.[0];
              setPreview(null);
              setContent(file ? await readText(file) : null);
            }}
          />
        </label>
        <button
          type="button"
          disabled={!content || send.isPending}
          onClick={() => send.mutate("preview")}
        >
          Ver qué cambia
        </button>
      </div>
      {send.isError && (
        <p className="clients__error" role="alert">
          {send.error.message}
        </p>
      )}
      {preview && (
        <section className="clients__contacts" aria-label="Vista previa">
          <h4>{preview.applied ? "Aplicado" : "Vista previa"}</h4>
          <p>
            {preview.creates.length} altas, {preview.changes.length} cambios, {preview.unchanged}{" "}
            sin cambios y {preview.errors.length} errores.
          </p>
          {preview.errors.length > 0 && (
            <ul className="clients__contact-list" aria-label="Errores">
              {preview.errors.map((row) => (
                <li key={`e${row.row}`} className="clients__error">
                  Fila {row.row} ({row.name || "sin nombre"}): {row.detail}
                </li>
              ))}
            </ul>
          )}
          <ul className="clients__contact-list" aria-label="Altas y cambios">
            {preview.creates.map((row) => (
              <li key={`c${row.row}`}>Alta: {row.name}</li>
            ))}
            {preview.changes.map((row) => (
              <li key={`m${row.row}`}>
                Cambio: {row.name} ({row.detail})
              </li>
            ))}
          </ul>
          {!preview.applied && preview.errors.length === 0 && (
            <button
              type="button"
              className="btn--primary"
              disabled={send.isPending}
              onClick={() => send.mutate("apply")}
            >
              Aplicar
            </button>
          )}
          {preview.errors.length > 0 && (
            <p className="muted">Corregí el archivo y volvé a subirlo: no se aplicó nada.</p>
          )}
        </section>
      )}
    </section>
  );
}
