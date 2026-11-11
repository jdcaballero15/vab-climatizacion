import { useState, type FormEvent } from "react";

import { useWorkTypes } from "../work-types/useWorkTypes";
import { CHANNEL_LABELS } from "./labels";
import type { OrderChannel, OrderListItem } from "./types";
import { useCreateOrder, useOrderClosure } from "./useOrders";

/**
 * Orden de reparación a partir del cierre de otra (E04-13): mismo cliente, domicilio y
 * equipo, y la observación de la escuadrilla como descripción, para revisar antes de
 * guardar. Las dos órdenes quedan relacionadas.
 */
export function RepairOrderForm({
  order,
  onCreated,
  onCancel,
}: {
  order: OrderListItem;
  onCreated: (number: number) => void;
  onCancel: () => void;
}) {
  const closure = useOrderClosure(order.id);
  const workTypes = useWorkTypes(false);
  const create = useCreateOrder();
  const [workTypeId, setWorkTypeId] = useState("");
  const [channel, setChannel] = useState<OrderChannel | "">("");
  const [description, setDescription] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);
  // Hasta que el usuario la toque, la descripción es la observación del cierre.
  const text = description ?? closure.data?.observation ?? "";
  const id = (field: string) => `repair-${order.id}-${field}`;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workTypeId || !channel || !text.trim()) {
      setMissing(true);
      return;
    }
    setMissing(false);
    create.mutate(
      {
        client_id: order.client_id,
        client_site_id: order.client_site_id,
        work_type_id: workTypeId,
        channel,
        description: text.trim(),
        equipment_id: order.equipment?.id ?? null,
        source_order_id: order.id,
        kind: "on_site",
      },
      { onSuccess: (nueva) => onCreated(nueva.number) },
    );
  }

  return (
    <form
      className="clients__form"
      onSubmit={handleSubmit}
      aria-label={`Orden de reparación desde la N° ${order.number}`}
    >
      <h4>Abrir orden de reparación</h4>
      <p className="muted">
        {order.client_name} · {order.site_label ?? order.site_address}
        {order.equipment && ` · Equipo ${order.equipment.internal_code}`}
      </p>
      <label htmlFor={id("work-type")}>Tipo de trabajo</label>
      <select
        id={id("work-type")}
        value={workTypeId}
        onChange={(e) => setWorkTypeId(e.target.value)}
      >
        <option value="">Elegí un tipo</option>
        {(workTypes.data ?? []).map((type) => (
          <option key={type.id} value={type.id}>
            {type.name}
          </option>
        ))}
      </select>
      <label htmlFor={id("channel")}>Canal</label>
      <select
        id={id("channel")}
        value={channel}
        onChange={(e) => setChannel(e.target.value as OrderChannel | "")}
      >
        <option value="">Por dónde llegó el pedido</option>
        {Object.entries(CHANNEL_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <label htmlFor={id("description")}>Descripción</label>
      <textarea
        id={id("description")}
        value={text}
        maxLength={2000}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Qué hay que reparar"
      />
      {missing && (
        <p className="clients__error" role="alert">
          Completá el tipo de trabajo, el canal y la descripción.
        </p>
      )}
      {create.isError && (
        <p className="clients__error" role="alert">
          {create.error.message}
        </p>
      )}
      <button type="submit" className="btn--primary" disabled={create.isPending}>
        {create.isPending ? "Guardando…" : "Crear orden de reparación"}
      </button>
      <button type="button" onClick={onCancel}>
        Cancelar
      </button>
    </form>
  );
}
