import { useState, type FormEvent } from "react";

import { NameTakenError } from "./useWorkTypes";

interface NewNameFormProps {
  label: string;
  submitLabel: string;
  isPending: boolean;
  error: Error | null;
  nameTakenMessage: string;
  onCreate: (name: string, reset: () => void) => void;
}

/** Alta de un valor de catálogo: solo pide el nombre. */
export function NewNameForm({
  label,
  submitLabel,
  isPending,
  error,
  nameTakenMessage,
  onCreate,
}: NewNameFormProps) {
  const [name, setName] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onCreate(name, () => setName(""));
  }

  return (
    <form className="catalog__new" onSubmit={handleSubmit}>
      <input
        aria-label={label}
        value={name}
        onChange={(event) => setName(event.target.value)}
        required
      />
      <button type="submit" disabled={isPending}>
        {submitLabel}
      </button>
      {error && (
        <p className="catalog__error" role="alert">
          {error instanceof NameTakenError ? nameTakenMessage : "No se pudo guardar."}
        </p>
      )}
    </form>
  );
}
