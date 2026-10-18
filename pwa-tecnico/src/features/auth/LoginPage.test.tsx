import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LoginPage } from "./LoginPage";

describe("LoginPage", () => {
  it("muestra el formulario de inicio de sesión en español", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { name: "OT Técnico" })).toBeInTheDocument();
    expect(screen.getByLabelText("Correo electrónico")).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Iniciar sesión" })).toBeInTheDocument();
  });
});
