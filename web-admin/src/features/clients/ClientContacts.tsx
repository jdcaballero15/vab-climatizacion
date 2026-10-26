import { useState, type FormEvent } from "react";

import { siteName } from "./labels";
import type { Contact, ContactCreate, Site } from "./types";
import { useContacts, useCreateContact, useSites, useUpdateContact } from "./useClients";

const EMPTY_CONTACT: ContactCreate = {
  client_site_id: null,
  name: null,
  phone: null,
  email: null,
  receives_monthly_report: false,
};

interface ContactFieldsProps {
  idPrefix: string;
  values: ContactCreate;
  sites: Site[];
  onChange: (values: ContactCreate) => void;
}

function ContactFields({ idPrefix, values, sites, onChange }: ContactFieldsProps) {
  const id = (field: string) => `${idPrefix}-${field}`;
  // Se ofrecen los activos; uno inactivo solo aparece si el contacto ya estaba asociado.
  const options = sites.filter((site) => site.is_active || site.id === values.client_site_id);
  return (
    <>
      <label htmlFor={id("site")}>Domicilio</label>
      <select
        id={id("site")}
        value={values.client_site_id ?? ""}
        onChange={(event) => onChange({ ...values, client_site_id: event.target.value || null })}
      >
        <option value="">Del cliente en general</option>
        {options.map((site) => (
          <option key={site.id} value={site.id}>
            {siteName(site)}
          </option>
        ))}
      </select>
      <label htmlFor={id("name")}>Nombre del contacto</label>
      <input
        id={id("name")}
        value={values.name ?? ""}
        onChange={(event) => onChange({ ...values, name: event.target.value || null })}
        maxLength={255}
      />
      <label htmlFor={id("phone")}>Teléfono</label>
      <input
        id={id("phone")}
        type="tel"
        value={values.phone ?? ""}
        onChange={(event) => onChange({ ...values, phone: event.target.value || null })}
        maxLength={50}
      />
      <label htmlFor={id("email")}>Email</label>
      <input
        id={id("email")}
        type="email"
        value={values.email ?? ""}
        onChange={(event) => onChange({ ...values, email: event.target.value || null })}
        maxLength={255}
      />
      <label className="clients__check">
        <input
          type="checkbox"
          checked={values.receives_monthly_report ?? false}
          onChange={(event) =>
            onChange({ ...values, receives_monthly_report: event.target.checked })
          }
        />
        Recibe el informe mensual
      </label>
    </>
  );
}

// Solo los campos editables: el backend rechaza campos de más (id, client_id).
function editable({
  client_site_id,
  name,
  phone,
  email,
  receives_monthly_report,
}: Contact): ContactCreate {
  return { client_site_id, name, phone, email, receives_monthly_report };
}

interface ContactRowProps {
  clientId: string;
  contact: Contact;
  sites: Site[];
}

function ContactRow({ clientId, contact, sites }: ContactRowProps) {
  const updateContact = useUpdateContact(clientId, contact.id);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<ContactCreate>(() => editable(contact));

  function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateContact.mutate(draft, { onSuccess: () => setEditing(false) });
  }

  const label = contact.name ?? contact.email ?? contact.phone ?? "Contacto";
  const site = sites.find((item) => item.id === contact.client_site_id);

  if (editing) {
    return (
      <li aria-label={label}>
        <form className="clients__form" onSubmit={handleSave} aria-label={`Editar ${label}`}>
          <ContactFields
            idPrefix={`contact-${contact.id}`}
            values={draft}
            sites={sites}
            onChange={setDraft}
          />
          {updateContact.isError && (
            <p className="clients__error" role="alert">
              {updateContact.error.message}
            </p>
          )}
          <button type="submit" disabled={updateContact.isPending}>
            Guardar
          </button>
          <button
            type="button"
            onClick={() => {
              updateContact.reset();
              setEditing(false);
            }}
          >
            Cancelar
          </button>
        </form>
      </li>
    );
  }

  return (
    <li className="clients__contact" aria-label={label}>
      <span>{contact.name ?? "Sin nombre"}</span>
      {site && <span className="catalog__badge">{siteName(site)}</span>}
      <span>{contact.phone ?? ""}</span>
      <span>{contact.email ?? ""}</span>
      {contact.receives_monthly_report && <span className="catalog__badge">Informe mensual</span>}
      <button
        type="button"
        aria-label={`Editar ${label}`}
        onClick={() => {
          setDraft(editable(contact));
          setEditing(true);
        }}
      >
        Editar
      </button>
    </li>
  );
}

/** Contactos de un cliente: todos opcionales, al menos un dato cada uno. Sin domicilio, el
 * contacto es del cliente en general. */
export function ClientContacts({ clientId }: { clientId: string }) {
  const contacts = useContacts(clientId);
  const sites = useSites(clientId).data ?? [];
  const createContact = useCreateContact(clientId);
  const [nuevo, setNuevo] = useState<ContactCreate>(EMPTY_CONTACT);

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createContact.mutate(nuevo, { onSuccess: () => setNuevo(EMPTY_CONTACT) });
  }

  return (
    <section className="clients__contacts">
      <h4>Contactos</h4>

      {contacts.isLoading && <p>Cargando contactos…</p>}
      {contacts.isError && <p role="alert">No se pudieron cargar los contactos.</p>}
      {contacts.data?.length === 0 && <p>Este cliente no tiene contactos cargados.</p>}
      {contacts.data && contacts.data.length > 0 && (
        <ul className="clients__contact-list">
          {contacts.data.map((contact) => (
            <ContactRow key={contact.id} clientId={clientId} contact={contact} sites={sites} />
          ))}
        </ul>
      )}

      <form className="clients__form" onSubmit={handleCreate} aria-label="Agregar contacto">
        <ContactFields
          idPrefix={`new-contact-${clientId}`}
          values={nuevo}
          sites={sites}
          onChange={setNuevo}
        />
        {createContact.isError && (
          <p className="clients__error" role="alert">
            {createContact.error.message}
          </p>
        )}
        <button type="submit" disabled={createContact.isPending}>
          Agregar contacto
        </button>
      </form>
    </section>
  );
}
