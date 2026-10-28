import { Wrench } from "lucide-react";

interface WrongRolePageProps {
  onLogout: () => void;
}

// Un usuario de la oficina que entra a la app del técnico: la API le niega la lista de
// órdenes, así que en lugar de quedar trabado se le avisa y se le deja salir.
export function WrongRolePage({ onLogout }: WrongRolePageProps) {
  return (
    <main className="login">
      <section className="login__form" aria-labelledby="wrong-role-title">
        <span className="login__mark" aria-hidden="true">
          <Wrench size={22} />
        </span>
        <h1 id="wrong-role-title" className="login__title">
          Esta app es para las escuadrillas
        </h1>
        <p className="login__subtitle">
          Tu usuario es de la oficina. Para trabajar con las órdenes, entrá a la administración.
        </p>
        <button type="button" onClick={onLogout}>
          Cerrar sesión
        </button>
      </section>
    </main>
  );
}
