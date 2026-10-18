import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { UpdateBanner } from "./UpdateBanner";

// Criterio 3: cuando hay una versión nueva, se avisa y se puede aplicar sin reinstalar.
describe("UpdateBanner", () => {
  it("no muestra nada cuando no hay actualización pendiente", () => {
    render(<UpdateBanner show={false} onUpdate={() => {}} />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("avisa y permite actualizar cuando hay una versión nueva", async () => {
    const onUpdate = vi.fn();
    render(<UpdateBanner show onUpdate={onUpdate} />);

    expect(screen.getByText("Hay una nueva versión disponible.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Actualizar" }));

    expect(onUpdate).toHaveBeenCalledOnce();
  });
});
