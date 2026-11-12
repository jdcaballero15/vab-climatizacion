import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { PageHeader } from "../../app/PageHeader";
import { useFailures } from "../failures/useFailures";
import { useParts } from "../parts/useParts";
import { useRepairs } from "../repairs/useRepairs";

type Kind = components["schemas"]["PromoteRequest"]["kind"];
type OtherText = components["schemas"]["OtherTextOut"];

const KINDS: Record<Kind, string> = {
  failure: "Fallas",
  repair: "Reparaciones",
  part: "Materiales",
};
const KEY = ["other-texts"] as const;

function saveError(error: unknown, fallback: string): Error {
  const detail = (error as { detail?: { message?: unknown } } | undefined)?.detail;
  return new Error(typeof detail?.message === "string" ? detail.message : fallback);
}

/**
 * Lo que las escuadrillas escribieron en "Otro", agrupado y con sus repeticiones (E02-07).
 * Se suma a la lista (nuevo o como uno que ya existe) y las órdenes pasan a usarlo, o se
 * descarta y deja de aparecer.
 */
export function OtherTextsPage() {
  const [kind, setKind] = useState<Kind>("failure");
  const texts = useQuery<OtherText[]>({
    queryKey: [...KEY, kind],
    queryFn: async () => {
      const { data, error } = await api.GET("/admin/other-texts", {
        params: { query: { kind } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los textos");
      }
      return data;
    },
  });

  return (
    <section className="catalog">
      <PageHeader
        eyebrow="Catálogos"
        title="Textos de «Otro»"
        subtitle="Lo que se repite se suma a la lista; las órdenes anteriores pasan a usarlo."
      />
      <div className="clients__filters" role="group" aria-label="Qué revisar">
        {(Object.keys(KINDS) as Kind[]).map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={kind === value}
            className={kind === value ? "btn--primary" : undefined}
            onClick={() => setKind(value)}
          >
            {KINDS[value]}
          </button>
        ))}
      </div>
      {texts.isLoading && <p>Cargando…</p>}
      {texts.isError && <p role="alert">No se pudieron cargar los textos.</p>}
      {texts.data?.length === 0 && <p>No hay textos de «Otro» para revisar.</p>}
      <ul className="clients__contact-list" aria-label={`Textos de ${KINDS[kind]}`}>
        {texts.data?.map((item) => (
          <TextRow key={item.text_key} kind={kind} item={item} />
        ))}
      </ul>
    </section>
  );
}

function TextRow({ kind, item }: { kind: Kind; item: OtherText }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(item.text);
  const [targetId, setTargetId] = useState("");
  const [failureId, setFailureId] = useState("");
  const failures = useFailures(null, false);
  const repairs = useRepairs(null, null, false);
  const parts = useParts(false);
  const existing =
    kind === "failure" ? failures.data : kind === "repair" ? repairs.data : parts.data;
  const promote = useMutation<{ updated: number }, Error>({
    mutationFn: async () => {
      const { data, error } = await api.POST("/admin/other-texts/promote", {
        body: {
          kind,
          text_key: item.text_key,
          name: targetId ? null : name,
          target_id: targetId || null,
          failure_id: kind === "repair" && !targetId ? failureId || null : null,
        },
      });
      if (error || !data) {
        throw saveError(error, "No se pudo sumar a la lista.");
      }
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });
  const dismiss = useMutation<void, Error>({
    mutationFn: async () => {
      const { error } = await api.POST("/admin/other-texts/dismiss", {
        body: { kind, text_key: item.text_key },
      });
      if (error) {
        throw saveError(error, "No se pudo descartar.");
      }
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  });

  return (
    <li className="clients__contact" aria-label={item.text}>
      <strong>{item.text}</strong>
      <span className="catalog__badge">
        {item.count} {item.count === 1 ? "vez" : "veces"}
      </span>
      <button type="button" onClick={() => setOpen((shown) => !shown)} aria-expanded={open}>
        Sumar a la lista
      </button>
      <button type="button" disabled={dismiss.isPending} onClick={() => dismiss.mutate()}>
        Descartar
      </button>
      {open && (
        <div className="clients__form">
          <label>
            Es uno que ya existe{" "}
            <select value={targetId} onChange={(event) => setTargetId(event.target.value)}>
              <option value="">No, crear uno nuevo</option>
              {existing?.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </select>
          </label>
          {!targetId && (
            <label>
              Nombre en la lista{" "}
              <input value={name} maxLength={255} onChange={(e) => setName(e.target.value)} />
            </label>
          )}
          {!targetId && kind === "repair" && (
            <label>
              Falla a la que pertenece{" "}
              <select value={failureId} onChange={(event) => setFailureId(event.target.value)}>
                <option value="">Elegí</option>
                {failures.data?.map((failure) => (
                  <option key={failure.id} value={failure.id}>
                    {failure.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {promote.isError && (
            <p className="clients__error" role="alert">
              {promote.error.message}
            </p>
          )}
          <button
            type="button"
            className="btn--primary"
            disabled={promote.isPending || (kind === "repair" && !targetId && !failureId)}
            onClick={() => promote.mutate()}
          >
            Confirmar
          </button>
        </div>
      )}
    </li>
  );
}
