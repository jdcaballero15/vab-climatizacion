import { useState, type FormEvent } from "react";

import type { ClientSummary } from "../clients/types";
import { useSites } from "../clients/useClients";
import { useWorkTypes } from "../work-types/useWorkTypes";
import { ClientPicker } from "./ClientPicker";
import { activeSites, EMPTY_ORDER, missingFields, type OrderFormValues } from "./formValues";
import { CHANNEL_LABELS } from "./labels";
import { SitePicker } from "./SitePicker";
import type { OrderChannel } from "./types";
import { useCreateOrder } from "./useOrders";

/** Alta de una orden a partir del pedido de un cliente. Queda Pendiente. */
export function OrderForm() {
  const [client, setClient] = useState<ClientSummary | null>(null);
  const [draft, setDraft] = useState<OrderFormValues>(EMPTY_ORDER);
  const [missing, setMissing] = useState<string | null>(null);
  const [created, setCreated] = useState<number | null>(null);
  const sites = useSites(client?.id ?? "", { enabled: client !== null });
  const workTypes = useWorkTypes(false);
  const createOrder = useCreateOrder();
  const active = activeSites(sites.data);
  // Con un solo domicilio activo se usa ese; con varios, el elegido (sin valor por defecto).
  const values: OrderFormValues = {
    ...draft,
    clientId: client?.id ?? null,
    siteId: active.length === 1 ? active[0].id : draft.siteId,
  };
  const set = (changes: Partial<OrderFormValues>) => setDraft({ ...draft, ...changes });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const problem = missingFields(values);
    setMissing(problem);
    if (problem || !values.clientId || !values.channel) {
      return;
    }
    createOrder.mutate(
      {
        client_id: values.clientId,
        client_site_id: values.siteId,
        work_type_id: values.workTypeId,
        channel: values.channel,
        description: values.description,
        requester_name: values.requesterName || null,
        requester_area: values.requesterArea || null,
      },
      {
        onSuccess: (orden) => {
          setCreated(orden.number);
          setClient(null);
          setDraft(EMPTY_ORDER);
        },
      },
    );
  }

  return (
    <section className="orders__new" aria-label="Nueva orden">
      <h3>Nueva orden</h3>
      {created !== null && <p role="status">Orden N° {created} creada.</p>}

      <ClientPicker
        selected={client}
        onSelect={(elegido) => {
          setClient(elegido);
          set({ siteId: "" });
          setCreated(null);
        }}
      />
      {client && (
        <SitePicker
          clientId={client.id}
          sites={sites}
          value={values.siteId}
          onChange={(siteId) => set({ siteId })}
        />
      )}

      <form className="clients__form" onSubmit={handleSubmit} aria-label="Datos del pedido">
        <label htmlFor="order-work-type">Tipo de trabajo</label>
        <select
          id="order-work-type"
          value={values.workTypeId}
          onChange={(event) => set({ workTypeId: event.target.value })}
        >
          <option value="">Elegí un tipo</option>
          {(workTypes.data ?? []).map((type) => (
            <option key={type.id} value={type.id}>
              {type.name}
            </option>
          ))}
        </select>
        <label htmlFor="order-channel">Canal</label>
        <select
          id="order-channel"
          value={values.channel}
          onChange={(event) => set({ channel: event.target.value as OrderChannel | "" })}
        >
          <option value="">Por dónde llegó el pedido</option>
          {Object.entries(CHANNEL_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <label htmlFor="order-description">Descripción del pedido</label>
        <textarea
          id="order-description"
          value={values.description}
          onChange={(event) => set({ description: event.target.value })}
          placeholder="Qué pasa y qué pide el cliente"
          maxLength={2000}
        />
        <label htmlFor="order-requester-name">Quién pidió</label>
        <input
          id="order-requester-name"
          value={values.requesterName}
          onChange={(event) => set({ requesterName: event.target.value })}
          placeholder="Nombre y cargo (opcional)"
          maxLength={255}
        />
        <label htmlFor="order-requester-area">Dónde</label>
        <input
          id="order-requester-area"
          value={values.requesterArea}
          onChange={(event) => set({ requesterArea: event.target.value })}
          placeholder="Sector, piso o ala (opcional)"
          maxLength={255}
        />
        {missing && (
          <p className="clients__error" role="alert">
            {missing}
          </p>
        )}
        {createOrder.isError && (
          <p className="clients__error" role="alert">
            {createOrder.error.message}
          </p>
        )}
        <button type="submit" disabled={createOrder.isPending}>
          Crear orden
        </button>
      </form>
    </section>
  );
}
