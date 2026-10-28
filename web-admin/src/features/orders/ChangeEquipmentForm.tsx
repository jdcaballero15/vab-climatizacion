import { useState, type FormEvent } from "react";

import { EquipmentSelect } from "./EquipmentSelect";
import type { OrderListItem } from "./types";
import { useChangeEquipment } from "./useOrders";

interface ChangeEquipmentFormProps {
  order: OrderListItem;
  onChanged: () => void;
  onClose: () => void;
}

/** Agregar, cambiar o sacar el equipo de una orden que todavía no se inició (E04-12). */
export function ChangeEquipmentForm({ order, onChanged, onClose }: ChangeEquipmentFormProps) {
  const changeEquipment = useChangeEquipment(order.id);
  const [equipmentId, setEquipmentId] = useState(order.equipment?.id ?? "");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    changeEquipment.mutate({ equipment_id: equipmentId || null }, { onSuccess: onChanged });
  }

  return (
    <form
      className="clients__form"
      onSubmit={handleSubmit}
      aria-label={`Equipo de la orden N° ${order.number}`}
    >
      <EquipmentSelect
        id={`equipment-${order.id}`}
        clientId={order.client_id}
        siteId={order.client_site_id}
        value={equipmentId}
        onChange={setEquipmentId}
      />
      {order.assignment && (
        <p className="muted">
          {order.assignment.crew_name} lo ve en el celular la próxima vez que actualiza.
        </p>
      )}
      {changeEquipment.isError && (
        <p className="clients__error" role="alert">
          {changeEquipment.error.message}
        </p>
      )}
      <button type="submit" disabled={changeEquipment.isPending}>
        Guardar equipo
      </button>
      <button type="button" onClick={onClose}>
        Volver
      </button>
    </form>
  );
}
