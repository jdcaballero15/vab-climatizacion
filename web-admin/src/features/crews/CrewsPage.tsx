import { useState } from "react";

import { CatalogItem } from "../catalogs/CatalogItem";
import { NewNameForm } from "../catalogs/NewNameForm";
import type { UserAdmin } from "../users/types";
import { useUsers } from "../users/useUsers";
import type { Crew, FieldTechnician } from "./types";
import {
  useCreateCrew,
  useCreateFieldTechnician,
  useCrews,
  useFieldTechnicians,
  useUpdateCrew,
  useUpdateFieldTechnician,
} from "./useCrews";
import { PageHeader } from "../../app/PageHeader";

const CREW_NAME_TAKEN = "Ya existe una escuadrilla con ese nombre (puede estar desactivada).";
const TECHNICIAN_NAME_TAKEN = "Ya existe un técnico con ese nombre (puede estar desactivado).";

/** Escuadrillas (con el usuario de su celular) y técnicos que se tildan al cerrar (D-013). */
export function CrewsPage() {
  return (
    <section className="catalog">
      <PageHeader
        eyebrow="Equipo"
        title="Escuadrillas y técnicos"
        subtitle={
          "Cada escuadrilla entra a la app con el usuario de su celular. Las personas que van " +
          "en cada una cambian: al cerrar una orden se tilda qué técnicos fueron."
        }
      />
      <CrewsSection />
      <FieldTechniciansSection />
    </section>
  );
}

function CrewsSection() {
  const [showInactive, setShowInactive] = useState(false);
  const crews = useCrews(showInactive);
  // Para saber qué usuarios del celular están libres hay que ver todas, activas o no.
  const allCrews = useCrews(true);
  const users = useUsers();
  const create = useCreateCrew();
  const taken = new Set(
    (allCrews.data ?? []).flatMap((crew) => (crew.app_user ? [crew.app_user.id] : [])),
  );

  return (
    <section aria-labelledby="crews-title">
      <h3 id="crews-title">Escuadrillas</h3>
      <NewNameForm
        label="Nueva escuadrilla"
        submitLabel="Agregar escuadrilla"
        isPending={create.isPending}
        error={create.error}
        nameTakenMessage={CREW_NAME_TAKEN}
        onCreate={(name, reset) => create.mutate(name, { onSuccess: reset })}
      />
      <ShowInactive checked={showInactive} onChange={setShowInactive} label="desactivadas" />
      {crews.isLoading && <p>Cargando escuadrillas…</p>}
      {crews.isError && <p role="alert">No se pudieron cargar las escuadrillas.</p>}
      {crews.data?.length === 0 && <p>Todavía no hay escuadrillas.</p>}
      {crews.data && crews.data.length > 0 && (
        <ul className="catalog__list">
          {crews.data.map((crew) => (
            <CrewItem key={crew.id} crew={crew} users={users.data ?? []} taken={taken} />
          ))}
        </ul>
      )}
    </section>
  );
}

interface CrewItemProps {
  crew: Crew;
  users: UserAdmin[];
  taken: Set<string>;
}

function CrewItem({ crew, users, taken }: CrewItemProps) {
  const update = useUpdateCrew(crew.id);
  // Mutaciones aparte para activar y para el celular: sus errores (409 con órdenes
  // abiertas, 422 de usuario) se muestran con el mensaje del backend, no el genérico.
  const updateStatus = useUpdateCrew(crew.id);
  const updateUser = useUpdateCrew(crew.id);
  const current = crew.app_user?.id ?? "";
  const options = users
    .filter(
      (user) =>
        user.id === current ||
        (user.role === "technician" && user.is_active && !taken.has(user.id)),
    )
    .sort((a, b) => a.full_name.localeCompare(b.full_name, "es"));
  const selectId = `crew-user-${crew.id}`;

  return (
    <CatalogItem
      name={crew.name}
      isActive={crew.is_active}
      isPending={update.isPending || updateStatus.isPending}
      error={update.error}
      nameTakenMessage={CREW_NAME_TAKEN}
      onSave={(changes) =>
        changes.is_active === undefined ? update.mutate(changes) : updateStatus.mutate(changes)
      }
    >
      <div className="catalog__row">
        <label htmlFor={selectId}>Celular de {crew.name}</label>
        <select
          id={selectId}
          value={current}
          disabled={updateUser.isPending}
          onChange={(event) => updateUser.mutate({ app_user_id: event.target.value || null })}
        >
          <option value="">Sin celular</option>
          {options.map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name}
            </option>
          ))}
        </select>
      </div>
      {crew.app_user && !crew.app_user.is_active && (
        <p className="catalog__error">El usuario del celular está inactivo.</p>
      )}
      {updateStatus.isError && (
        <p className="catalog__error" role="alert">
          {updateStatus.error.message}
        </p>
      )}
      {updateUser.isError && (
        <p className="catalog__error" role="alert">
          {updateUser.error.message}
        </p>
      )}
    </CatalogItem>
  );
}

function FieldTechniciansSection() {
  const [showInactive, setShowInactive] = useState(false);
  const technicians = useFieldTechnicians(showInactive);
  const create = useCreateFieldTechnician();

  return (
    <section aria-labelledby="field-technicians-title">
      <h3 id="field-technicians-title">Técnicos</h3>
      <NewNameForm
        label="Nuevo técnico"
        submitLabel="Agregar técnico"
        isPending={create.isPending}
        error={create.error}
        nameTakenMessage={TECHNICIAN_NAME_TAKEN}
        onCreate={(name, reset) => create.mutate(name, { onSuccess: reset })}
      />
      <ShowInactive checked={showInactive} onChange={setShowInactive} label="desactivados" />
      {technicians.isLoading && <p>Cargando técnicos…</p>}
      {technicians.isError && <p role="alert">No se pudieron cargar los técnicos.</p>}
      {technicians.data?.length === 0 && <p>Todavía no hay técnicos.</p>}
      {technicians.data && technicians.data.length > 0 && (
        <ul className="catalog__list">
          {technicians.data.map((technician) => (
            <FieldTechnicianItem key={technician.id} technician={technician} />
          ))}
        </ul>
      )}
    </section>
  );
}

function FieldTechnicianItem({ technician }: { technician: FieldTechnician }) {
  const update = useUpdateFieldTechnician(technician.id);
  return (
    <CatalogItem
      name={technician.full_name}
      isActive={technician.is_active}
      isPending={update.isPending}
      error={update.error}
      nameTakenMessage={TECHNICIAN_NAME_TAKEN}
      onSave={({ name, is_active }) => update.mutate({ full_name: name, is_active })}
    />
  );
}

interface ShowInactiveProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}

function ShowInactive({ checked, onChange, label }: ShowInactiveProps) {
  return (
    <label className="catalog__toggle">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      Mostrar {label}
    </label>
  );
}
