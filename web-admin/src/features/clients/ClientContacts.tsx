import { useState, type FormEvent } from "react";

import type { Contact, ContactCreate } from "./types";
import { useContacts, useCreateContact, useUpdateContact } from "./useClients";

const EMPTY_CONTACT: ContactCreate = {
  name: null,
  phone: null,
  email: null,
  receives_monthly_report: false,
};

interface ContactFieldsProps {
  idPrefix: string;
  values: ContactCreate;
  onChange: (values: ContactCreate) => void;
}

function ContactFields({ idPrefix, values, onChange }: ContactFieldsProps) {
  const id = (field: string) => `${idPrefix}-${field}`;
  return (
    <>
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
function editable({ name, phone, email, receives_monthly_report }: Contact): ContactCreate {
  return { name, phone, email, receives_monthly_report };
}

function ContactRow({ clientId, contact }: { clientId: string; contact: Contact }) {
  const updateContact = useUpdateContact(clientId, contact.id);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<ContactCreate>(() => editable(contact));

  function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateContact.mutate(draft, { onSuccess: () => setEditing(false) });
  }

  const label = contact.name ?? contact.email ?? contact.phone ?? "Contacto";

  if (editing) {
    return (
      <li>
        <form className="clients__form" onSubmit={handleSave} aria-label={`Editar ${label}`}>
          <ContactFields idPrefix={`contact-${contact.id}`} values={draft} onChange={setDraft} />
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
    <li className="clients__contact">
      <span>{contact.name ?? "Sin nombre"}</span>
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

/** Contactos de un cliente: todos opcionales, al menos un dato cada uno. */
export function ClientContacts({ clientId }: { clientId: string }) {
  const contacts = useContacts(clientId);
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
            <ContactRow key={contact.id} clientId={clientId} contact={contact} />
          ))}
        </ul>
      )}

      <form className="clients__form" onSubmit={handleCreate} aria-label="Agregar contacto">
        <ContactFields idPrefix={`new-contact-${clientId}`} values={nuevo} onChange={setNuevo} />
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
