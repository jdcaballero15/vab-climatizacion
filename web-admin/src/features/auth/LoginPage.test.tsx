import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LoginPage } from "./LoginPage";

// Criterio 4: la ruta raíz muestra una pantalla de inicio de sesión vacía en español.
describe("LoginPage", () => {
  it("muestra el formulario de inicio de sesión en español", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { name: "OT Platform" })).toBeInTheDocument();
    expect(screen.getByLabelText("Correo electrónico")).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Iniciar sesión" })).toBeInTheDocument();
  });

  it("empieza con los campos vacíos", () => {
    render(<LoginPage />);

    expect(screen.getByLabelText("Correo electrónico")).toHaveValue("");
    expect(screen.getByLabelText("Contraseña")).toHaveValue("");
  });
});
